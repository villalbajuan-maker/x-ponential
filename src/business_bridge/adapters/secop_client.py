from __future__ import annotations

import logging
import random
import time
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import requests  # type: ignore[import-untyped]

from business_bridge.core.audit import log_event
from business_bridge.adapters.secop_constants import (
    DEFAULT_LIMIT,
    DEFAULT_TIMEOUT,
    RETRYABLE_STATUS_CODES,
    SODA_METADATA_URL,
    SODA_RESOURCE_URL,
    USER_AGENT,
)
from business_bridge.adapters.secop_models import DatasetMetadataInfo
from business_bridge.adapters.secop_utils import _format_epoch, _first_non_empty, _utc_now_iso, _unique_preserve_order, escape_soql


LOG = logging.getLogger("secop")


class SocrataError(RuntimeError):
    """Se lanza cuando una solicitud o carga util de Socrata no se puede procesar."""

    pass


class SocrataClient:
    """Cliente HTTP pequeno con reintentos y cache de metadatos para las APIs Socrata."""

    def __init__(
        self,
        app_token: Optional[str] = None,
        timeout: Tuple[int, int] = DEFAULT_TIMEOUT,
        max_retries: int = 4,
        backoff_factor: float = 0.8,
        user_agent: str = USER_AGENT,
        session: Optional[requests.Session] = None,
    ) -> None:
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.session = session or requests.Session()
        self.session.headers.setdefault("User-Agent", user_agent)
        if app_token:
            self.session.headers["X-App-Token"] = app_token
        self._metadata_cache: Dict[str, DatasetMetadataInfo] = {}

    def _request_json(self, url: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """Hacer una peticion GET y devolver el JSON decodificado."""

        last_error: Optional[Exception] = None
        for attempt in range(self.max_retries + 1):
            try:
                response = self.session.get(url, params=params, timeout=self.timeout)
            except requests.RequestException as exc:
                last_error = exc
                if attempt >= self.max_retries:
                    raise SocrataError(f"Network error while requesting {url}: {exc}") from exc
                self._sleep_backoff(attempt, None)
                continue

            if 200 <= response.status_code < 300:
                try:
                    return response.json()
                except ValueError as exc:
                    raise SocrataError(f"Invalid JSON returned by Socrata for {url}") from exc

            if response.status_code not in RETRYABLE_STATUS_CODES or attempt >= self.max_retries:
                detail = response.text[:500].strip()
                raise SocrataError(
                    f"Socrata request failed ({response.status_code}) for {url}: {detail}"
                )

            last_error = SocrataError(f"HTTP {response.status_code} while requesting {url}")
            self._sleep_backoff(attempt, response.headers.get("Retry-After"))

        raise SocrataError(f"Unable to complete request to {url}: {last_error}")

    def _sleep_backoff(self, attempt: int, retry_after: Optional[str]) -> None:
        """Dormir con backoff exponencial respetando Retry-After cuando exista."""

        delay = self.backoff_factor * (2**attempt)
        if retry_after:
            try:
                delay = max(delay, float(retry_after))
            except ValueError:
                pass
        delay = min(delay + random.uniform(0.0, 0.25), 10.0)
        time.sleep(delay)

    def get_metadata(self, dataset_id: str) -> DatasetMetadataInfo:
        """Traer y cachear metadatos de Socrata para un id de conjunto de datos."""

        if dataset_id in self._metadata_cache:
            return self._metadata_cache[dataset_id]

        payload = self._request_json(SODA_METADATA_URL.format(dataset_id=dataset_id))
        columns = [
            column.get("fieldName", "")
            for column in payload.get("columns", [])
            if column.get("fieldName")
        ]
        metadata = DatasetMetadataInfo(
            dataset_id=dataset_id,
            dataset_name=_first_non_empty(payload.get("name"), dataset_id),
            queried_at=_utc_now_iso(),
            last_update="no disponible",
            last_update_source="no disponible",
            publication_date=_format_epoch(payload.get("publicationDate")),
            rows_updated_at=_format_epoch(payload.get("rowsUpdatedAt")),
            view_last_modified=_format_epoch(payload.get("viewLastModified")),
            created_at=_format_epoch(payload.get("createdAt")),
            columns=columns,
            source_url=SODA_METADATA_URL.format(dataset_id=dataset_id),
        )

        for source_name, value in (
            ("rowsUpdatedAt", payload.get("rowsUpdatedAt")),
            ("viewLastModified", payload.get("viewLastModified")),
            ("publicationDate", payload.get("publicationDate")),
            ("createdAt", payload.get("createdAt")),
        ):
            formatted = _format_epoch(value)
            if formatted:
                metadata.last_update = formatted
                metadata.last_update_source = source_name
                break

        self._metadata_cache[dataset_id] = metadata
        return metadata

    def query_rows(
        self,
        dataset_id: str,
        where: Optional[str] = None,
        select: Optional[str] = None,
        order: Optional[str] = None,
        limit: int = DEFAULT_LIMIT,
        offset: int = 0,
        extra_params: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Consultar un conjunto de datos con filtros SOQL opcionales y paginacion."""

        params: Dict[str, Any] = {"$limit": int(limit), "$offset": int(offset)}
        if where:
            params["$where"] = where
        if select:
            params["$select"] = select
        if order:
            params["$order"] = order
        if extra_params:
            params.update(extra_params)
        payload = self._request_json(SODA_RESOURCE_URL.format(dataset_id=dataset_id), params=params)
        if not isinstance(payload, list):
            raise SocrataError(
                f"Unexpected response type for dataset {dataset_id}: {type(payload)!r}"
            )
        return payload

    def iter_rows(
        self,
        dataset_id: str,
        where: Optional[str] = None,
        select: Optional[str] = None,
        order: Optional[str] = None,
        page_size: int = 100,
        max_rows: Optional[int] = None,
    ) -> Iterable[Dict[str, Any]]:
        """Iterar por las filas del conjunto de datos usando paginacion simple por paginas."""

        offset = 0
        collected = 0
        while True:
            rows = self.query_rows(
                dataset_id=dataset_id,
                where=where,
                select=select,
                order=order,
                limit=page_size,
                offset=offset,
            )
            if not rows:
                break
            for row in rows:
                yield row
                collected += 1
                if max_rows is not None and collected >= max_rows:
                    return
            if len(rows) < page_size:
                break
            offset += page_size

    def query_exact_any(
        self,
        dataset_id: str,
        field_names: Sequence[str],
        candidate_values: Sequence[str],
        limit: int = DEFAULT_LIMIT,
    ) -> List[Dict[str, Any]]:
        """Buscar en un conjunto de datos cualquier coincidencia exacta entre los valores candidatos."""

        values = _unique_preserve_order(candidate_values)
        if not values:
            return []
        clauses: List[str] = []
        for field_name in field_names:
            for candidate in values:
                clauses.append("%s = '%s'" % (field_name, escape_soql(candidate)))
        where = " OR ".join(clauses)
        try:
            return self.query_rows(dataset_id=dataset_id, where=where, limit=limit)
        except SocrataError as exc:
            log_event(
                logging.WARNING,
                "secop.query_failed",
                dataset_id,
                error_type=exc.__class__.__name__,
                error_message=str(exc),
            )
            return []

    def query_exact_first(
        self,
        dataset_id: str,
        field_names: Sequence[str],
        candidate_values: Sequence[str],
        limit: int = DEFAULT_LIMIT,
    ) -> Optional[Dict[str, Any]]:
        """Devolver la primera fila exacta o None cuando no haya coincidencias."""

        rows = self.query_exact_any(dataset_id, field_names, candidate_values, limit=limit)
        return rows[0] if rows else None
