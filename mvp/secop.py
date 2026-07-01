#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import json
import logging
import os
import random
import re
import sys
import threading
import time
import webbrowser
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass, field, is_dataclass
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple
from urllib.parse import parse_qs, quote_plus, urlparse

import requests
from fastapi import APIRouter, HTTPException as FastAPIHTTPException
from fastapi.responses import Response


LOG = logging.getLogger("secop")

# Identificadores oficiales de los conjuntos de datos usados por el inspector.
DATASETS = {
    "secop_ii_procesos": "p6dx-8zbt",
    "secop_i_procesos_desde_2018": "f789-7hwg",
    "secop_i_procesos_hasta_2017": "qddk-cgux",
    "secop_i_archivos_desde_2019": "ps88-5e3v",
    "secop_i_archivos_hasta_2018": "8kpz-m6cc",
    "secop_ii_archivos_2022": "kgcd-kt7i",
    "secop_ii_archivos_2023": "3skv-9na7",
    "secop_ii_archivos_2024": "nbae-kzan",
    "secop_ii_archivos_desde_2025": "dmgg-8hin",
}

SODA_RESOURCE_URL = "https://www.datos.gov.co/resource/{dataset_id}.json"
SODA_METADATA_URL = "https://www.datos.gov.co/api/views/{dataset_id}.json"

SECOP_II_PROCESS_FIELDS = ("id_del_proceso", "referencia_del_proceso")
SECOP_I_PROCESS_FIELDS = ("numero_de_constancia", "numero_de_proceso", "uid")
SECOP_II_DOCUMENT_FIELDS = ("proceso", "n_mero_de_contrato")
SECOP_I_DOCUMENT_FIELDS = ("numero_de_constancia",)
SECOP_II_PROCESS_TEXT_FIELDS = (
    "nombre_del_procedimiento",
    "descripci_n_del_procedimiento",
    "entidad",
    "fase",
    "estado_del_procedimiento",
    "modalidad_de_contratacion",
)
SECOP_I_PROCESS_TEXT_FIELDS = (
    "objeto_del_contrato_a_la",
    "detalle_del_objeto_a_contratar",
    "objeto_a_contratar",
    "nombre_entidad",
    "numero_de_proceso",
    "numero_de_constancia",
    "uid",
    "estado_del_proceso",
)
SECOP_II_DOCUMENT_TEXT_FIELDS = (
    "nombre_archivo",
    "descripci_n",
    "entidad",
    "proceso",
    "n_mero_de_contrato",
)
SECOP_I_DOCUMENT_TEXT_FIELDS = (
    "titulo",
    "descripcion",
    "nombrearchivo",
    "numero_de_constancia",
    "palabras_clave",
)

SECOP_II_DOMAINS = ("community.secop.gov.co", "www.secop.gov.co", "secop.gov.co")
SECOP_I_DOMAINS = ("contratos.gov.co", "www.contratos.gov.co", "www.colombiacompra.gov.co", "colombiacompra.gov.co")
SECOP_DOWNLOAD_HOSTS = SECOP_II_DOMAINS + SECOP_I_DOMAINS + ("20.96.127.85",)

SECOP_II_ID_RE = re.compile(r"^CO1\.[A-Z0-9]+(?:\.[A-Z0-9]+)+$", re.IGNORECASE)
SECOP_II_NOTICE_RE = re.compile(r"CO1\.NTC\.\d+", re.IGNORECASE)
SECOP_I_CONSTANCIA_RE = re.compile(r"^\d{2}-\d{2}-\d{6,8}$")
SECOP_GENERIC_REFERENCE_RE = re.compile(r"^[A-Z0-9][A-Z0-9\s./_-]{2,}$", re.IGNORECASE)

RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}
DEFAULT_TIMEOUT = (10, 30)
DEFAULT_LIMIT = 25
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8009
USER_AGENT = "NORDECOL-SECOP-Script/0.1 (+local; requests)"
SEARCH_MAX_TOKENS = 14
SEARCH_MIN_TOKEN_LENGTH = 4


def escape_soql(value: str) -> str:
    """Escapar una cadena para usarla dentro de una clausula simple de igualdad SOQL."""
    return value.replace("'", "''")


def _utc_now_iso() -> str:
    """Devolver la hora local actual en formato ISO."""
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _format_epoch(value: Any) -> str:
    """Convertir un valor tipo epoch de Socrata en una fecha legible."""
    if value in (None, "", 0):
        return ""
    try:
        if isinstance(value, str) and value.strip():
            value = float(value)
        if isinstance(value, (int, float)):
            dt = datetime.fromtimestamp(float(value), tz=timezone.utc).astimezone()
            return dt.isoformat(timespec="seconds")
    except (TypeError, ValueError, OSError):
        return ""
    return ""


def _first_non_empty(*values: Any) -> str:
    """Devolver el primer valor no vacio convertido a cadena."""
    for value in values:
        if value is None:
            continue
        if isinstance(value, str):
            stripped = value.strip()
            if stripped:
                return stripped
        else:
            return str(value)
    return ""


def _extract_url(value: Any) -> str:
    """Extraer una URL desde un objeto anidado de Socrata o desde una cadena simple."""
    if isinstance(value, dict):
        return _first_non_empty(value.get("url"), value.get("href"), value.get("value"))
    return _first_non_empty(value)


def _normalize_text(value: str) -> str:
    """Normalizar espacios para que la tokenizacion y el matching sean consistentes."""
    return " ".join(value.strip().split())


def _tokenize_search_terms(*values: Any, max_tokens: int = SEARCH_MAX_TOKENS) -> List[str]:
    """Extraer una lista compacta de tokens reutilizables desde valores arbitrarios."""
    tokens: List[str] = []
    seen = set()
    for value in values:
        if value is None:
            continue
        if isinstance(value, dict):
            value = " ".join(_first_non_empty(item) for item in value.values())
        text = _normalize_text(_first_non_empty(value)).lower()
        if not text:
            continue
        for token in re.findall(r"[a-z0-9]+", text):
            if token in seen:
                continue
            if token.isdigit():
                if len(token) < 4:
                    continue
            elif len(token) < SEARCH_MIN_TOKEN_LENGTH and token not in {"dane", "geih", "secop", "co1", "ntc", "req"}:
                continue
            seen.add(token)
            tokens.append(token)
            if len(tokens) >= max_tokens:
                return tokens
    return tokens


def _casefold_dict_lookup(payload: Mapping[str, Any], key: str) -> Optional[Any]:
    """Buscar una clave de diccionario sin importar diferencias de mayusculas."""
    wanted = key.casefold()
    for existing_key, value in payload.items():
        if existing_key.casefold() == wanted:
            return value
    return None


def _is_url(value: str) -> bool:
    """Comprobar si la cadena ya parece una URL."""
    parsed = urlparse(value)
    return bool(parsed.scheme and parsed.netloc)


def _is_allowed_download_url(value: str) -> bool:
    """Permitir descargas solo desde los dominios SECOP y los hosts oficiales."""
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return False
    hostname = (parsed.hostname or "").lower()
    if hostname in SECOP_DOWNLOAD_HOSTS:
        return True
    return any(hostname.endswith(f".{allowed}") for allowed in SECOP_DOWNLOAD_HOSTS if "." in allowed)


def _collect_query_params(query: str) -> Dict[str, List[str]]:
    """Parsear una cadena de consulta en un mapa que preserve parametros repetidos."""
    params = parse_qs(query, keep_blank_values=True)
    return {key: list(values) for key, values in params.items()}


def _query_param_case_insensitive(params: Mapping[str, Sequence[str]], *names: str) -> List[str]:
    """Recolectar valores de parametros sin importar el caso de las claves."""
    wanted = {name.casefold() for name in names}
    values: List[str] = []
    for key, items in params.items():
        if key.casefold() in wanted:
            values.extend([item for item in items if item])
    return values


def _unique_preserve_order(values: Iterable[str]) -> List[str]:
    """Eliminar duplicados preservando el primer orden de aparicion."""
    seen = set()
    ordered: List[str] = []
    for value in values:
        normalized = value.strip()
        if not normalized:
            continue
        if normalized in seen:
            continue
        seen.add(normalized)
        ordered.append(normalized)
    return ordered


def _json_safe(value: Any) -> Any:
    """Convertir dataclasses anidadas y objetos complejos en valores seguros para JSON."""
    if is_dataclass(value):
        return _json_safe(asdict(value))
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    return value


@dataclass(frozen=True)
class ParsedSecopInput:
    """Representacion normalizada de la consulta SECOP del usuario."""
    raw_value: str
    input_kind: str
    platform: str
    identifier: str
    original_url: str = ""
    domain: str = ""
    path: str = ""
    query_params: Dict[str, List[str]] = field(default_factory=dict)
    matched_parameters: Tuple[str, ...] = ()
    identifier_candidates: Tuple[str, ...] = ()

    def to_dict(self) -> Dict[str, Any]:
        """Serializar la entrada parseada a primitivas seguras para JSON."""
        return _json_safe(self)


@dataclass
class DatasetMetadataInfo:
    """Instantanea de metadatos para un conjunto de datos de Socrata."""
    dataset_id: str
    dataset_name: str
    queried_at: str
    last_update: str
    last_update_source: str
    publication_date: str = ""
    rows_updated_at: str = ""
    view_last_modified: str = ""
    created_at: str = ""
    columns: List[str] = field(default_factory=list)
    source_url: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Serializar los metadatos del dataset a primitivas seguras para JSON."""
        return _json_safe(self)


@dataclass
class DocumentInfo:
    """Registro normalizado de documento usado por la UI y la API del inspector."""
    dataset_id: str
    dataset_name: str
    source_family: str
    dataset_source_url: str
    process_identifier: str
    document_identifier: str
    title: str
    file_name: str
    extension: str
    description: str
    entity: str = ""
    contract_number: str = ""
    download_url: str = ""
    official_url: str = ""
    source_field: str = ""
    raw_row: Dict[str, Any] = field(default_factory=dict, repr=False)

    def to_dict(self) -> Dict[str, Any]:
        """Serializar el registro del documento a primitivas seguras para JSON."""
        return _json_safe(self)


@dataclass
class InspectionResult:
    """Respuesta completa devuelta por una ejecucion de inspeccion."""
    queried_at: str
    parsed_input: ParsedSecopInput
    metadata: List[DatasetMetadataInfo]
    process_rows: List[Dict[str, Any]]
    documents: List[DocumentInfo]
    document_groups: List[Dict[str, Any]] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Serializar el resultado de inspeccion a primitivas seguras para JSON."""
        return _json_safe(self)


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
        delay = self.backoff_factor * (2 ** attempt)
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
        columns = [column.get("fieldName", "") for column in payload.get("columns", []) if column.get("fieldName")]
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
            raise SocrataError(f"Unexpected response type for dataset {dataset_id}: {type(payload)!r}")
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
            LOG.warning("Query failed for dataset %s: %s", dataset_id, exc)
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


def parse_secop_input(value: str) -> ParsedSecopInput:
    """Clasificar la entrada del usuario como SECOP I, SECOP II, URL, id o referencia."""
    raw_value = (value or "").strip()
    if not raw_value:
        return ParsedSecopInput(
            raw_value="",
            input_kind="empty",
            platform="unknown",
            identifier="",
        )

    is_url = _is_url(raw_value)
    original_url = raw_value if is_url else ""
    domain = ""
    path = ""
    params: Dict[str, List[str]] = {}
    matched_parameters: List[str] = []
    identifier_candidates: List[str] = []
    identifier = raw_value
    platform = "unknown"
    input_kind = "reference"

    if is_url:
        # Primero revisamos la URL buscando parametros SECOP conocidos y marcas de plataforma.
        parsed = urlparse(raw_value)
        domain = parsed.netloc.lower()
        path = parsed.path
        params = _collect_query_params(parsed.query)
        normalized_path = parsed.path.lower()

        secop_ii_domain = any(domain.endswith(item) for item in SECOP_II_DOMAINS)
        secop_i_domain = any(domain.endswith(item) for item in SECOP_I_DOMAINS)

        notice_values = _query_param_case_insensitive(params, "noticeUID", "processUID", "processId", "id")
        constancia_values = _query_param_case_insensitive(
            params,
            "numConstancia",
            "numeroConstancia",
            "idProceso",
            "IDProceso",
        )

        if secop_ii_domain or "public/tendering/opportunitydetail/index" in normalized_path or notice_values:
            platform = "secop_ii"
            input_kind = "url"
            if notice_values:
                identifier_candidates.extend(notice_values)
                matched_parameters.extend([name for name in params if name.casefold() in {"noticeuid", "processuid", "processid", "id"}])
            else:
                regex_matches = SECOP_II_NOTICE_RE.findall(raw_value)
                if regex_matches:
                    identifier_candidates.extend(regex_matches)
                    matched_parameters.append("noticeUID-regex")
                else:
                    generic_matches = SECOP_II_ID_RE.findall(raw_value)
                    if generic_matches:
                        identifier_candidates.extend(generic_matches)
                        matched_parameters.append("secop-ii-id")
            if not identifier_candidates and raw_value:
                identifier_candidates.append(raw_value)

        elif secop_i_domain or constancia_values:
            platform = "secop_i"
            input_kind = "url"
            if constancia_values:
                identifier_candidates.extend(constancia_values)
                matched_parameters.extend(
                    [name for name in params if name.casefold() in {"numconstancia", "numeroconstancia", "idproceso"}]
                )
            else:
                if SECOP_I_CONSTANCIA_RE.match(raw_value):
                    identifier_candidates.append(raw_value)
                    matched_parameters.append("constancia-directa")
            if not identifier_candidates and raw_value:
                identifier_candidates.append(raw_value)

        else:
            identifier_candidates.append(raw_value)

    else:
        # El texto plano se compara contra patrones SECOP conocidos y sus respaldos.
        if SECOP_II_ID_RE.match(raw_value) or SECOP_II_NOTICE_RE.match(raw_value):
            platform = "secop_ii"
            input_kind = "identifier"
            identifier_candidates.append(raw_value)
            matched_parameters.append("secop-ii-id")
        elif SECOP_I_CONSTANCIA_RE.match(raw_value):
            platform = "secop_i"
            input_kind = "constancia"
            identifier_candidates.append(raw_value)
            matched_parameters.append("constancia")
        elif raw_value.upper().startswith("CO1."):
            platform = "secop_ii"
            input_kind = "identifier"
            identifier_candidates.append(raw_value)
            matched_parameters.append("secop-ii-prefix")
        else:
            input_kind = "reference"
            identifier_candidates.append(raw_value)
            if SECOP_GENERIC_REFERENCE_RE.match(raw_value):
                matched_parameters.append("generic-reference")

    identifier_candidates = _unique_preserve_order(identifier_candidates)
    identifier = identifier_candidates[0] if identifier_candidates else raw_value

    return ParsedSecopInput(
        raw_value=raw_value,
        input_kind=input_kind,
        platform=platform,
        identifier=identifier,
        original_url=original_url,
        domain=domain,
        path=path,
        query_params=params,
        matched_parameters=tuple(_unique_preserve_order(matched_parameters)),
        identifier_candidates=tuple(identifier_candidates),
    )


def _candidate_dataset_families(platform: str) -> Dict[str, List[str]]:
    """Devolver las familias de conjuntos de datos que se deben consultar para una plataforma."""
    if platform == "secop_ii":
        # Aunque la entrada sea SECOP II, tambien cruzamos contra el historial de SECOP I.
        return {
            "process": [
                DATASETS["secop_ii_procesos"],
                DATASETS["secop_i_procesos_desde_2018"],
                DATASETS["secop_i_procesos_hasta_2017"],
            ],
            "documents": [
                DATASETS["secop_ii_archivos_2022"],
                DATASETS["secop_ii_archivos_2023"],
                DATASETS["secop_ii_archivos_2024"],
                DATASETS["secop_ii_archivos_desde_2025"],
                DATASETS["secop_i_archivos_desde_2019"],
                DATASETS["secop_i_archivos_hasta_2018"],
            ],
        }
    if platform == "secop_i":
        # Aunque la entrada sea SECOP I, tambien dejamos SECOP II como respaldo por cruces historicos.
        return {
            "process": [
                DATASETS["secop_i_procesos_desde_2018"],
                DATASETS["secop_i_procesos_hasta_2017"],
                DATASETS["secop_ii_procesos"],
            ],
            "documents": [
                DATASETS["secop_i_archivos_desde_2019"],
                DATASETS["secop_i_archivos_hasta_2018"],
                DATASETS["secop_ii_archivos_2022"],
                DATASETS["secop_ii_archivos_2023"],
                DATASETS["secop_ii_archivos_2024"],
                DATASETS["secop_ii_archivos_desde_2025"],
            ],
        }
    # Si no logramos clasificar la fuente, consultamos ambas familias completas.
    return {
        "process": [
            DATASETS["secop_ii_procesos"],
            DATASETS["secop_i_procesos_desde_2018"],
            DATASETS["secop_i_procesos_hasta_2017"],
        ],
        "documents": [
            DATASETS["secop_ii_archivos_2022"],
            DATASETS["secop_ii_archivos_2023"],
            DATASETS["secop_ii_archivos_2024"],
            DATASETS["secop_ii_archivos_desde_2025"],
            DATASETS["secop_i_archivos_desde_2019"],
            DATASETS["secop_i_archivos_hasta_2018"],
        ],
    }


def _dataset_family_label(dataset_id: str) -> str:
    """Etiquetar un id de conjunto de datos como SECOP I o SECOP II."""
    secop_ii_ids = {
        DATASETS["secop_ii_procesos"],
        DATASETS["secop_ii_archivos_2022"],
        DATASETS["secop_ii_archivos_2023"],
        DATASETS["secop_ii_archivos_2024"],
        DATASETS["secop_ii_archivos_desde_2025"],
    }
    return "SECOP II" if dataset_id in secop_ii_ids else "SECOP I"


def _normalize_process_row(row: Mapping[str, Any]) -> Dict[str, Any]:
    """Aplanar campos URL anidados en filas de proceso para mostrarlos mejor."""
    normalized = dict(row)
    if isinstance(normalized.get("urlproceso"), dict):
        normalized["urlproceso"] = normalized["urlproceso"].get("url", "")
    if isinstance(normalized.get("ruta_proceso_en_secop_i"), dict):
        normalized["ruta_proceso_en_secop_i"] = normalized["ruta_proceso_en_secop_i"].get("url", "")
    return normalized


def _process_row_key(row: Mapping[str, Any]) -> Tuple[str, str, str, str, str, str]:
    """Construir una llave de deduplicacion para filas de proceso."""
    return (
        _first_non_empty(row.get("dataset_id")),
        _first_non_empty(row.get("id_del_proceso")),
        _first_non_empty(row.get("referencia_del_proceso")),
        _first_non_empty(row.get("numero_de_constancia")),
        _first_non_empty(row.get("numero_de_proceso")),
        _first_non_empty(row.get("uid")),
    )


def _process_summary_from_row(dataset_id: str, row: Mapping[str, Any], dataset_name: str) -> Dict[str, Any]:
    """Convertir una fila de proceso en el resumen compacto que ve la UI."""
    if dataset_id == DATASETS["secop_ii_procesos"]:
        return {
            "dataset_id": dataset_id,
            "dataset_name": dataset_name,
            "process_id": _first_non_empty(row.get("id_del_proceso")),
            "reference": _first_non_empty(row.get("referencia_del_proceso")),
            "entity": _first_non_empty(row.get("entidad")),
            "title": _first_non_empty(row.get("nombre_del_procedimiento")),
            "status": _first_non_empty(row.get("estado_del_procedimiento"), row.get("fase")),
            "amount": _first_non_empty(row.get("precio_base")),
            "document_url": _extract_url(row.get("urlproceso")),
        }

    return {
        "dataset_id": dataset_id,
        "dataset_name": dataset_name,
        "process_id": _first_non_empty(row.get("numero_de_constancia")),
        "reference": _first_non_empty(row.get("numero_de_proceso"), row.get("uid")),
        "entity": _first_non_empty(row.get("nombre_entidad")),
        "title": _first_non_empty(row.get("objeto_a_contratar"), row.get("detalle_del_objeto_a_contratar")),
        "status": _first_non_empty(row.get("estado_del_proceso")),
        "amount": _first_non_empty(row.get("cuantia_proceso")),
        "document_url": _extract_url(row.get("ruta_proceso_en_secop_i")),
    }


def _document_from_row(dataset_id: str, row: Mapping[str, Any], dataset_name: str, dataset_source_url: str) -> DocumentInfo:
    """Convertir una fila de documento en el modelo normalizado de documento."""
    if dataset_id in {
        DATASETS["secop_ii_archivos_2022"],
        DATASETS["secop_ii_archivos_2023"],
        DATASETS["secop_ii_archivos_2024"],
        DATASETS["secop_ii_archivos_desde_2025"],
    }:
        download_url = _extract_url(row.get("url_descarga_documento"))
        official_url = download_url
        return DocumentInfo(
            dataset_id=dataset_id,
            dataset_name=dataset_name,
            source_family=_dataset_family_label(dataset_id),
            dataset_source_url=dataset_source_url,
            process_identifier=_first_non_empty(row.get("proceso")),
            document_identifier=_first_non_empty(row.get("id_documento")),
            title=_first_non_empty(row.get("nombre_archivo"), row.get("descripci_n")),
            file_name=_first_non_empty(row.get("nombre_archivo")),
            extension=_first_non_empty(row.get("extensi_n")),
            description=_first_non_empty(row.get("descripci_n")),
            entity=_first_non_empty(row.get("entidad")),
            contract_number=_first_non_empty(row.get("n_mero_de_contrato")),
            download_url=download_url,
            official_url=official_url,
            source_field="proceso|n_mero_de_contrato",
            raw_row=dict(row),
        )

    download_url = _extract_url(row.get("ruta_descarga"))
    return DocumentInfo(
        dataset_id=dataset_id,
        dataset_name=dataset_name,
        source_family=_dataset_family_label(dataset_id),
        dataset_source_url=dataset_source_url,
        process_identifier=_first_non_empty(row.get("numero_de_constancia")),
        document_identifier=_first_non_empty(row.get("identificador")),
        title=_first_non_empty(row.get("titulo"), row.get("nombrearchivo")),
        file_name=_first_non_empty(row.get("nombrearchivo")),
        extension=_first_non_empty(row.get("extension")),
        description=_first_non_empty(row.get("descripcion")),
        entity="",
        contract_number=_first_non_empty(row.get("numero_de_constancia")),
        download_url=download_url,
        official_url=download_url,
        source_field="numero_de_constancia",
        raw_row=dict(row),
    )


def _group_documents(documents: Sequence[DocumentInfo]) -> List[Dict[str, Any]]:
    """Agrupar documentos primero por familia de origen y luego por conjunto de datos."""
    grouped: List[Dict[str, Any]] = []
    source_index: Dict[str, Dict[str, Any]] = {}

    for doc in documents:
        source_key = doc.source_family or "Sin fuente"
        source_group = source_index.get(source_key)
        if source_group is None:
            source_group = {
                "source_family": source_key,
                "document_count": 0,
                "datasets": [],
            }
            source_group["_dataset_index"] = {}
            source_index[source_key] = source_group
            grouped.append(source_group)

        source_group["document_count"] += 1
        dataset_key = (doc.dataset_id, doc.dataset_name, doc.dataset_source_url)
        dataset_index: Dict[Tuple[str, str, str], Dict[str, Any]] = source_group["_dataset_index"]
        dataset_group = dataset_index.get(dataset_key)
        if dataset_group is None:
            dataset_group = {
                "dataset_id": doc.dataset_id,
                "dataset_name": doc.dataset_name,
                "dataset_source_url": doc.dataset_source_url,
                "document_count": 0,
                "documents": [],
            }
            dataset_index[dataset_key] = dataset_group
            source_group["datasets"].append(dataset_group)

        dataset_group["document_count"] += 1
        dataset_group["documents"].append(doc)

    for source_group in grouped:
        source_group.pop("_dataset_index", None)
        source_group["dataset_count"] = len(source_group["datasets"])
        for dataset_group in source_group["datasets"]:
            dataset_group["documents"] = [doc.to_dict() for doc in dataset_group["documents"]]

    return grouped


def _collect_metadata(client: SocrataClient, dataset_ids: Sequence[str]) -> List[DatasetMetadataInfo]:
    """Traer metadatos de varios conjuntos de datos en paralelo y preservar el orden pedido."""
    ordered_ids = _unique_preserve_order(dataset_ids)
    metadata: List[DatasetMetadataInfo] = []
    if not ordered_ids:
        return metadata
    with ThreadPoolExecutor(max_workers=min(8, len(ordered_ids))) as executor:
        futures = {executor.submit(client.get_metadata, dataset_id): dataset_id for dataset_id in ordered_ids}
        for future in as_completed(futures):
            try:
                metadata.append(future.result())
            except Exception as exc:
                dataset_id = futures[future]
                LOG.warning("Metadata fetch failed for %s: %s", dataset_id, exc)
                metadata.append(
                    DatasetMetadataInfo(
                        dataset_id=dataset_id,
                        dataset_name=dataset_id,
                        queried_at=_utc_now_iso(),
                        last_update="no disponible",
                        last_update_source="no disponible",
                        source_url=SODA_METADATA_URL.format(dataset_id=dataset_id),
                    )
                )
    metadata.sort(key=lambda item: ordered_ids.index(item.dataset_id) if item.dataset_id in ordered_ids else 999)
    return metadata


def _metadata_by_dataset_id(metadata: Sequence[DatasetMetadataInfo]) -> Dict[str, DatasetMetadataInfo]:
    """Indexar los metadatos por id de conjunto de datos para consultas rapidas."""
    return {item.dataset_id: item for item in metadata}


def _build_candidates(parsed: ParsedSecopInput) -> List[str]:
    """Armar los candidatos de identificador que se deben buscar por coincidencia exacta."""
    candidates = list(parsed.identifier_candidates or (parsed.identifier,))
    if parsed.query_params:
        candidates.extend(_query_param_case_insensitive(parsed.query_params, "noticeUID", "processUID", "processId", "id"))
        candidates.extend(
            _query_param_case_insensitive(
                parsed.query_params,
                "numConstancia",
                "numeroConstancia",
                "idProceso",
                "IDProceso",
            )
        )
    if parsed.platform == "secop_ii" and parsed.identifier and parsed.identifier.upper().startswith("CO1."):
        candidates.append(parsed.identifier)
    if parsed.platform == "secop_i" and parsed.identifier:
        candidates.append(parsed.identifier)
    return _unique_preserve_order(candidates)


def _search_process_rows(
    client: SocrataClient,
    parsed: ParsedSecopInput,
    dataset_ids: Sequence[str],
) -> List[Dict[str, Any]]:
    """Encontrar filas de proceso en los conjuntos de datos candidatos usando coincidencias exactas."""
    candidates = _build_candidates(parsed)
    results: List[Dict[str, Any]] = []
    for dataset_id in _unique_preserve_order(dataset_ids):
        if dataset_id == DATASETS["secop_ii_procesos"]:
            rows = client.query_exact_any(dataset_id, SECOP_II_PROCESS_FIELDS, candidates, limit=20)
        else:
            rows = client.query_exact_any(dataset_id, SECOP_I_PROCESS_FIELDS, candidates, limit=20)
        for row in rows:
            normalized = _normalize_process_row(row)
            normalized["dataset_id"] = dataset_id
            normalized["source_family"] = _dataset_family_label(dataset_id)
            if normalized not in results:
                results.append(normalized)

    return results


def _derive_document_candidates(parsed: ParsedSecopInput, process_rows: Sequence[Dict[str, Any]]) -> List[str]:
    """Derivar terminos de busqueda de documentos desde la entrada y las filas de proceso."""
    candidates = list(_build_candidates(parsed))
    for row in process_rows:
        candidates.extend(
            _unique_preserve_order(
                [
                    _first_non_empty(row.get("id_del_proceso")),
                    _first_non_empty(row.get("id_del_portafolio")),
                    _first_non_empty(row.get("referencia_del_proceso")),
                    _first_non_empty(row.get("numero_de_constancia")),
                    _first_non_empty(row.get("numero_de_proceso")),
                    _first_non_empty(row.get("uid")),
                ]
            )
        )
    return _unique_preserve_order(candidates)


def _search_documents(
    client: SocrataClient,
    parsed: ParsedSecopInput,
    process_rows: Sequence[Dict[str, Any]],
    dataset_ids: Sequence[str],
) -> List[DocumentInfo]:
    """Encontrar filas de documentos en los conjuntos de datos candidatos usando coincidencias exactas."""
    candidates = _derive_document_candidates(parsed, process_rows)
    docs: List[DocumentInfo] = []
    for dataset_id in _unique_preserve_order(dataset_ids):
        if dataset_id in {
            DATASETS["secop_ii_archivos_2022"],
            DATASETS["secop_ii_archivos_2023"],
            DATASETS["secop_ii_archivos_2024"],
            DATASETS["secop_ii_archivos_desde_2025"],
        }:
            rows = client.query_exact_any(dataset_id, SECOP_II_DOCUMENT_FIELDS, candidates, limit=20)
        else:
            rows = client.query_exact_any(dataset_id, SECOP_I_DOCUMENT_FIELDS, candidates, limit=20)
        metadata = client.get_metadata(dataset_id)
        dataset_name = metadata.dataset_name
        dataset_source_url = metadata.source_url
        for row in rows:
            docs.append(_document_from_row(dataset_id, row, dataset_name, dataset_source_url))

    unique_docs: List[DocumentInfo] = []
    seen_keys = set()
    for doc in docs:
        key = (doc.dataset_id, doc.document_identifier, doc.download_url, doc.file_name)
        if key in seen_keys:
            continue
        seen_keys.add(key)
        unique_docs.append(doc)
    return unique_docs


def inspect_secop_value(client: SocrataClient, value: str, *, metadata_limit: int = DEFAULT_LIMIT) -> InspectionResult:
    """Ejecutar el flujo completo de inspeccion SECOP para un valor de entrada."""
    parsed = parse_secop_input(value)
    families = _candidate_dataset_families(parsed.platform)
    # Cargamos contexto de ambas familias para que la UI siempre pueda mostrar comparacion completa.
    metadata_dataset_ids = families["process"] + families["documents"]
    metadata = _collect_metadata(client, metadata_dataset_ids)
    process_rows = _search_process_rows(client, parsed, families["process"])
    documents = _search_documents(client, parsed, process_rows, families["documents"])

    document_groups = _group_documents(documents)

    notes: List[str] = []
    if not process_rows:
        notes.append("No se encontró coincidencia exacta en los datasets de procesos consultados.")
    if not documents:
        notes.append("No se encontraron documentos exactos en los datasets de archivos consultados.")
    if parsed.platform == "unknown":
        notes.append("El input no reveló una plataforma con certeza; se consultaron ambas familias de datasets.")
    if parsed.input_kind == "empty":
        notes.append("El valor de entrada está vacío.")

    return InspectionResult(
        queried_at=_utc_now_iso(),
        parsed_input=parsed,
        metadata=metadata,
        process_rows=process_rows,
        documents=documents,
        document_groups=document_groups,
        notes=notes,
    )


def _render_simple_table(rows: Sequence[Mapping[str, Any]], keys: Sequence[str]) -> str:
    """Renderizar una tabla HTML compacta a partir de una lista de mapas."""
    if not rows:
        return "<div class='empty'>Sin filas.</div>"
    header = "".join(f"<th>{html.escape(key)}</th>" for key in keys)
    body_rows = []
    for row in rows:
        cells = []
        for key in keys:
            value = row.get(key, "")
            if isinstance(value, dict):
                value = value.get("url", json.dumps(value, ensure_ascii=False))
            cells.append(f"<td>{html.escape(_first_non_empty(value))}</td>")
        body_rows.append("<tr>" + "".join(cells) + "</tr>")
    return "<table><thead><tr>%s</tr></thead><tbody>%s</tbody></table>" % (header, "".join(body_rows))


def _render_process_summary(result: InspectionResult) -> Dict[str, Any]:
    """Devolver un resumen unico de proceso para la primera fila coincidente."""
    if not result.process_rows:
        return {}
    first_row = result.process_rows[0]
    dataset_id = _first_non_empty(first_row.get("dataset_id")) or (
        DATASETS["secop_ii_procesos"] if result.parsed_input.platform == "secop_ii" else DATASETS["secop_i_procesos_desde_2018"]
    )
    dataset_name = next((meta.dataset_name for meta in result.metadata if meta.dataset_id == dataset_id), dataset_id)
    return _process_summary_from_row(dataset_id, first_row, dataset_name)


def _render_process_family_summaries(result: InspectionResult) -> List[Dict[str, Any]]:
    """Devolver un resumen por familia SECOP para que la UI pinte ambas columnas."""
    metadata_by_id = _metadata_by_dataset_id(result.metadata)
    family_index: Dict[str, List[Dict[str, Any]]] = {}

    for row in result.process_rows:
        family = _first_non_empty(row.get("source_family")) or (
            "SECOP II" if _first_non_empty(row.get("dataset_id")) == DATASETS["secop_ii_procesos"] else "SECOP I"
        )
        family_index.setdefault(family, []).append(row)

    summaries: List[Dict[str, Any]] = []
    for family in ("SECOP I", "SECOP II"):
        rows = family_index.get(family, [])
        if rows:
            first_row = rows[0]
            dataset_id = _first_non_empty(first_row.get("dataset_id")) or (
                DATASETS["secop_ii_procesos"] if family == "SECOP II" else DATASETS["secop_i_procesos_desde_2018"]
            )
            dataset_name = metadata_by_id.get(dataset_id).dataset_name if dataset_id in metadata_by_id else dataset_id
            summary = _process_summary_from_row(dataset_id, first_row, dataset_name)
            summary["source_family"] = family
            summary["process_count"] = len(rows)
            summaries.append(summary)
        else:
            summaries.append(
                {
                    "source_family": family,
                    "process_count": 0,
                    "dataset_id": "",
                    "dataset_name": "",
                    "process_id": "",
                    "reference": "",
                    "entity": "",
                    "title": "",
                    "status": "",
                    "amount": "",
                    "document_url": "",
                }
            )

    extra_families = [family for family in family_index if family not in {"SECOP I", "SECOP II"}]
    for family in extra_families:
        rows = family_index.get(family, [])
        first_row = rows[0]
        dataset_id = _first_non_empty(first_row.get("dataset_id"))
        dataset_name = metadata_by_id.get(dataset_id).dataset_name if dataset_id in metadata_by_id else dataset_id
        summary = _process_summary_from_row(dataset_id, first_row, dataset_name)
        summary["source_family"] = family
        summary["process_count"] = len(rows)
        summaries.append(summary)

    return summaries


def _render_html_index() -> str:
    """Devolver el contenedor HTML local usado por el servidor del inspector embebido."""
    index_path = Path(__file__).with_name("mvp") / "index.html"
    if index_path.exists():
        return index_path.read_text(encoding="utf-8")
    return """<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>SECOP Inspector</title>
  <style>
    :root {
      color-scheme: dark;
      --bg: #0b1220;
      --panel: #101a2d;
      --panel-2: #16213a;
      --line: rgba(148,163,184,0.18);
      --text: #e5eefb;
      --muted: #9fb1cc;
      --accent: #7dd3fc;
      --accent-2: #fbbf24;
      --good: #34d399;
      --bad: #fb7185;
      --chip: #1f2b45;
      --shadow: 0 16px 32px rgba(0,0,0,.24);
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background:
        radial-gradient(circle at top left, rgba(125, 211, 252, 0.12), transparent 30%),
        radial-gradient(circle at top right, rgba(251, 191, 36, 0.10), transparent 24%),
        linear-gradient(180deg, #08101c 0%, #0b1220 100%);
      color: var(--text);
      min-height: 100vh;
    }
    .wrap { max-width: 1180px; margin: 0 auto; padding: 32px 18px 48px; }
    .hero {
      padding: 24px 24px 18px;
      border: 1px solid var(--line);
      border-radius: 24px;
      background: linear-gradient(180deg, rgba(16,26,45,.96), rgba(16,26,45,.82));
      box-shadow: var(--shadow);
      margin-bottom: 18px;
    }
    h1 { margin: 0 0 8px; font-size: clamp(28px, 4vw, 48px); letter-spacing: -0.03em; }
    .subtitle { color: var(--muted); max-width: 900px; line-height: 1.5; }
    .grid { display: grid; grid-template-columns: 1.1fr .9fr; gap: 18px; }
    .panel {
      border: 1px solid var(--line);
      border-radius: 20px;
      background: linear-gradient(180deg, rgba(22,33,58,.95), rgba(16,26,45,.95));
      box-shadow: var(--shadow);
      overflow: hidden;
    }
    .panel h2 {
      margin: 0;
      padding: 16px 18px;
      font-size: 15px;
      text-transform: uppercase;
      letter-spacing: 0.12em;
      color: var(--accent);
      border-bottom: 1px solid var(--line);
    }
    .content { padding: 18px; }
    .input-row {
      display: grid;
      grid-template-columns: 1fr auto;
      gap: 10px;
      margin-bottom: 12px;
    }
    input[type="text"] {
      width: 100%;
      padding: 14px 16px;
      border-radius: 14px;
      border: 1px solid rgba(148,163,184,.24);
      background: #0b1324;
      color: var(--text);
      outline: none;
      font-size: 14px;
    }
    button, .btnlink {
      border: 0;
      border-radius: 14px;
      padding: 13px 16px;
      background: linear-gradient(135deg, #38bdf8, #0ea5e9);
      color: #03111d;
      font-weight: 700;
      cursor: pointer;
      text-decoration: none;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
    }
    .btnlink.secondary {
      background: linear-gradient(135deg, #334155, #1f2937);
      color: var(--text);
      border: 1px solid rgba(148,163,184,.2);
    }
    .chips { display: flex; flex-wrap: wrap; gap: 8px; margin: 8px 0 0; }
    .chip {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 8px 10px;
      border-radius: 999px;
      background: var(--chip);
      color: var(--text);
      border: 1px solid rgba(148,163,184,.15);
      font-size: 12px;
    }
    .status {
      margin-top: 12px;
      padding: 12px 14px;
      border-radius: 14px;
      background: rgba(125, 211, 252, 0.08);
      border: 1px solid rgba(125, 211, 252, 0.2);
      color: var(--muted);
      white-space: pre-wrap;
    }
    .status.error {
      background: rgba(251,113,133,0.08);
      border-color: rgba(251,113,133,.28);
      color: #fecdd3;
    }
    .cards {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 12px;
      margin-top: 14px;
    }
    .card {
      border-radius: 16px;
      padding: 14px;
      border: 1px solid var(--line);
      background: rgba(8, 16, 28, 0.65);
    }
    .card .label { font-size: 11px; text-transform: uppercase; letter-spacing: 0.12em; color: var(--muted); }
    .card .value { margin-top: 8px; font-size: 14px; line-height: 1.45; word-break: break-word; }
    .section { margin-top: 18px; }
    .section h3 { margin: 0 0 10px; font-size: 14px; color: var(--accent-2); }
    table {
      width: 100%;
      border-collapse: collapse;
      overflow: hidden;
      border-radius: 14px;
      font-size: 13px;
      background: rgba(8, 16, 28, 0.6);
      border: 1px solid var(--line);
    }
    th, td {
      padding: 10px 12px;
      border-bottom: 1px solid rgba(148,163,184,.12);
      vertical-align: top;
      text-align: left;
    }
    th {
      position: sticky;
      top: 0;
      background: rgba(16,26,45,0.98);
      color: #cde7ff;
      font-weight: 700;
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.08em;
    }
    tr:hover td { background: rgba(125, 211, 252, 0.04); }
    .doc-item {
      border: 1px solid var(--line);
      border-radius: 16px;
      padding: 14px;
      margin-bottom: 12px;
      background: rgba(8, 16, 28, 0.55);
    }
    .doc-title { font-weight: 700; margin-bottom: 6px; }
    .doc-meta { color: var(--muted); font-size: 13px; line-height: 1.5; }
    .doc-actions { margin-top: 10px; display: flex; flex-wrap: wrap; gap: 8px; }
    .empty { color: var(--muted); padding: 14px 0; }
    pre {
      margin: 0;
      white-space: pre-wrap;
      word-break: break-word;
      background: rgba(8, 16, 28, 0.75);
      border: 1px solid var(--line);
      border-radius: 16px;
      padding: 14px;
      color: #dbeafe;
      max-height: 420px;
      overflow: auto;
    }
    .footer-note { margin-top: 16px; color: var(--muted); font-size: 12px; line-height: 1.5; }
    @media (max-width: 980px) {
      .grid { grid-template-columns: 1fr; }
      .cards { grid-template-columns: 1fr; }
      .input-row { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
  <div class="wrap">
    <section class="hero">
      <h1>SECOP Inspector</h1>
      <div class="subtitle">
        Pega un enlace, referencia o constancia de SECOP I o SECOP II. La consulta usa exclusivamente datasets oficiales de datos.gov.co,
        sin scraping de la interfaz HTML.
      </div>
      <div class="chips">
        <span class="chip">SECOP II: p6dx-8zbt</span>
        <span class="chip">SECOP I: f789-7hwg / qddk-cgux</span>
        <span class="chip">Archivos: ps88-5e3v / 8kpz-m6cc / kgcd-kt7i / 3skv-9na7 / nbae-kzan / dmgg-8hin</span>
      </div>
    </section>

    <div class="grid">
      <section class="panel">
        <h2>Consulta</h2>
        <div class="content">
          <div class="input-row">
            <input id="inputValue" type="text" placeholder="https://community.secop.gov.co/Public/Tendering/OpportunityDetail/Index?noticeUID=CO1.REQ.2577563" />
            <button id="inspectBtn">Consultar</button>
          </div>
          <div class="chips">
            <button class="btnlink secondary" data-sample="https://community.secop.gov.co/Public/Tendering/OpportunityDetail/Index?noticeUID=CO1.REQ.2577563">SECOP II ejemplo</button>
            <button class="btnlink secondary" data-sample="https://www.contratos.gov.co/consultas/detalleProceso.do?numConstancia=19-12-10176235">SECOP I ejemplo</button>
            <button class="btnlink secondary" data-sample="CO1.REQ.2577563">ID directo</button>
          </div>
          <div id="status" class="status">Listo para consultar.</div>
          <div class="section">
            <h3>Entrada parseada</h3>
            <div id="parsedCards" class="cards"></div>
          </div>
          <div class="section">
            <h3>Resumen del proceso</h3>
            <div id="processSummary"></div>
          </div>
          <div class="section">
            <h3>Notas</h3>
            <div id="notes"></div>
          </div>
        </div>
      </section>

      <section class="panel">
        <h2>Metadatos y documentos</h2>
        <div class="content">
          <div class="section">
            <h3>Datasets consultados</h3>
            <div id="metadataTable"></div>
          </div>
          <div class="section">
            <h3>Documentos relacionados</h3>
            <div id="documents"></div>
          </div>
          <div class="section">
            <h3>Salida cruda</h3>
            <pre id="rawJson">{}</pre>
          </div>
        </div>
      </section>
    </div>

    <div class="footer-note">
      La fecha de actualización de cada dataset se obtiene dinámicamente desde la API de metadatos. Si no está disponible, se muestra como
      "no disponible".
    </div>
  </div>

  <script>
    const input = document.getElementById('inputValue');
    const btn = document.getElementById('inspectBtn');
    const status = document.getElementById('status');
    const parsedCards = document.getElementById('parsedCards');
    const metadataTable = document.getElementById('metadataTable');
    const documents = document.getElementById('documents');
    const rawJson = document.getElementById('rawJson');
    const processSummary = document.getElementById('processSummary');
    const notes = document.getElementById('notes');

    function escapeHtml(text) {
      return String(text)
        .replaceAll('&', '&amp;')
        .replaceAll('<', '&lt;')
        .replaceAll('>', '&gt;')
        .replaceAll('"', '&quot;')
        .replaceAll("'", '&#39;');
    }

    function card(label, value) {
      return `<div class="card"><div class="label">${escapeHtml(label)}</div><div class="value">${escapeHtml(value || '—')}</div></div>`;
    }

    function renderParsed(parsed) {
      parsedCards.innerHTML = [
        card('Plataforma', parsed.platform),
        card('Tipo', parsed.input_kind),
        card('Identificador', parsed.identifier),
        card('Dominio', parsed.domain || '—'),
        card('Ruta', parsed.path || '—'),
        card('Parámetros', parsed.matched_parameters && parsed.matched_parameters.length ? parsed.matched_parameters.join(', ') : '—'),
      ].join('');
    }

    function renderMetadata(items) {
      if (!items || !items.length) {
        metadataTable.innerHTML = '<div class="empty">Sin metadatos.</div>';
        return;
      }
      const rows = items.map(item => `
        <tr>
          <td>${escapeHtml(item.dataset_name)}</td>
          <td>${escapeHtml(item.dataset_id)}</td>
          <td>${escapeHtml(item.last_update)}</td>
          <td>${escapeHtml(item.queried_at)}</td>
        </tr>
      `).join('');
      metadataTable.innerHTML = `
        <table>
          <thead>
            <tr>
              <th>Dataset</th>
              <th>ID</th>
              <th>Última actualización</th>
              <th>Consultado</th>
            </tr>
          </thead>
          <tbody>${rows}</tbody>
        </table>
      `;
    }

    function renderDocuments(items) {
      if (!items || !items.length) {
        documents.innerHTML = '<div class="empty">Sin documentos relacionados.</div>';
        return;
      }
      documents.innerHTML = items.map(item => `
        <div class="doc-item">
          <div class="doc-title">${escapeHtml(item.title || item.file_name || item.document_identifier || 'Documento')}</div>
          <div class="doc-meta">
            <div><strong>Dataset:</strong> ${escapeHtml(item.dataset_name)} (${escapeHtml(item.dataset_id)})</div>
            <div><strong>Proceso:</strong> ${escapeHtml(item.process_identifier || '—')}</div>
            <div><strong>Archivo:</strong> ${escapeHtml(item.file_name || '—')}</div>
            <div><strong>Extensión:</strong> ${escapeHtml(item.extension || '—')}</div>
            <div><strong>Descripción:</strong> ${escapeHtml(item.description || '—')}</div>
            <div><strong>Entidad:</strong> ${escapeHtml(item.entity || '—')}</div>
            <div><strong>URL:</strong> ${item.download_url ? `<a href="${escapeHtml(item.download_url)}" target="_blank" rel="noreferrer">${escapeHtml(item.download_url)}</a>` : '—'}</div>
          </div>
          <div class="doc-actions">
            ${item.download_url ? `<a class="btnlink" href="${escapeHtml(item.download_url)}" target="_blank" rel="noreferrer">Abrir oficial</a>` : ''}
          </div>
        </div>
      `).join('');
    }

    function renderNotes(items) {
      if (!items || !items.length) {
        notes.innerHTML = '<div class="empty">Sin notas.</div>';
        return;
      }
      notes.innerHTML = `<pre>${escapeHtml(items.join('\n'))}</pre>`;
    }

    function renderProcessSummary(data) {
      if (!data || !Object.keys(data).length) {
        processSummary.innerHTML = '<div class="empty">Sin coincidencias de proceso.</div>';
        return;
      }
      const keys = ['dataset_name', 'process_id', 'reference', 'entity', 'title', 'status', 'amount', 'document_url'];
      const rows = keys.map(key => `
        <tr>
          <td>${escapeHtml(key)}</td>
          <td>${escapeHtml(data[key] || '—')}</td>
        </tr>
      `).join('');
      processSummary.innerHTML = `<table><tbody>${rows}</tbody></table>`;
    }

    async function inspect(value) {
      const query = value || input.value.trim();
      if (!query) {
        status.textContent = 'Escribe un enlace, referencia o constancia antes de consultar.';
        status.className = 'status error';
        return;
      }
      status.className = 'status';
      status.textContent = 'Consultando datasets oficiales...';
      try {
        const response = await fetch('/api/inspect?value=' + encodeURIComponent(query));
        const data = await response.json();
        if (!response.ok) {
          throw new Error(data.detail || 'No se pudo completar la consulta.');
        }
        renderParsed(data.parsed_input);
        renderMetadata(data.metadata || []);
        renderDocuments(data.documents || []);
        renderNotes(data.notes || []);
        renderProcessSummary(data.process_summary || {});
        rawJson.textContent = JSON.stringify(data, null, 2);
        status.textContent = 'Consulta completa.';
      } catch (error) {
        status.className = 'status error';
        status.textContent = error.message || String(error);
      }
    }

    btn.addEventListener('click', () => inspect());
    input.addEventListener('keydown', (event) => {
      if (event.key === 'Enter') {
        inspect();
      }
    });
    document.querySelectorAll('[data-sample]').forEach(button => {
      button.addEventListener('click', () => {
        input.value = button.getAttribute('data-sample');
        inspect(input.value);
      });
    });
  </script>
</body>
</html>
"""


class SecopApp:
    """Capa de servicio ligera sobre el cliente Socrata y el flujo de inspeccion."""
    def __init__(self, client: Optional[SocrataClient] = None) -> None:
        self.client = client or SocrataClient(app_token=os.getenv("SECOP_APP_TOKEN"))

    def inspect(self, value: str) -> InspectionResult:
        """Inspeccionar una entrada del usuario contra los datasets oficiales."""
        return inspect_secop_value(self.client, value)

    def get_dataset_metadata(self, dataset_id: str) -> DatasetMetadataInfo:
        """Exponer metadatos cacheados del dataset a traves de un metodo de servicio."""
        return self.client.get_metadata(dataset_id)


secop_service = SecopApp()
secop_router = APIRouter(tags=["secop"])


@secop_router.get("/api/inspect")
def api_inspect(value: str = "") -> Dict[str, Any]:
    """Ruta FastAPI que devuelve todo el payload de inspeccion en JSON."""
    if not value.strip():
        raise FastAPIHTTPException(status_code=400, detail="Missing 'value' query parameter.")
    try:
        result = secop_service.inspect(value)
        payload = result.to_dict()
        payload["process_summary"] = _render_process_summary(result)
        payload["process_family_summaries"] = _render_process_family_summaries(result)
        return payload
    except Exception as exc:  # pragma: no cover - defensive server boundary
        LOG.exception("Inspection failed")
        raise FastAPIHTTPException(status_code=400, detail=str(exc)) from exc


@secop_router.get("/api/download")
def api_download(url: str = "", filename: str = "") -> Response:
    """Proxy de una descarga SECOP permitida de vuelta a quien la solicita."""
    if not url:
        raise FastAPIHTTPException(status_code=400, detail="Missing 'url' query parameter.")
    if not _is_allowed_download_url(url):
        raise FastAPIHTTPException(status_code=400, detail="The requested URL is not allowed.")
    try:
        response = requests.get(
            url,
            headers={"User-Agent": USER_AGENT, "Accept": "*/*"},
            timeout=DEFAULT_TIMEOUT,
            stream=True,
            allow_redirects=True,
        )
        response.raise_for_status()
        content_type = response.headers.get("Content-Type", "application/octet-stream")
        lower_content_type = content_type.lower()
        if "text/html" in lower_content_type or "application/xhtml" in lower_content_type:
            raise ValueError(
                "The SECOP URL returned HTML instead of a file. Open the official page and complete the manual step if the site asks for it."
            )
        content = response.content
        safe_name = _first_non_empty(filename, Path(urlparse(url).path).name, "secop-document")
        safe_name = re.sub(r"[^A-Za-z0-9._-]+", "_", safe_name).strip("._-") or "secop-document"
        return Response(
            content=content,
            media_type=content_type,
            headers={
                "Content-Disposition": f'attachment; filename="{safe_name}"',
                "X-File-Name": safe_name,
            },
        )
    except Exception as exc:  # pragma: no cover - defensive server boundary
        LOG.exception("Download proxy failed")
        raise FastAPIHTTPException(status_code=400, detail=str(exc)) from exc


@secop_router.get("/api/metadata")
def api_metadata(dataset_id: str = "") -> Dict[str, Any]:
    """Ruta FastAPI que devuelve metadatos para un dataset id."""
    if not dataset_id.strip():
        raise FastAPIHTTPException(status_code=400, detail="Missing 'dataset_id' query parameter.")
    try:
        metadata = secop_service.get_dataset_metadata(dataset_id)
        return metadata.to_dict()
    except Exception as exc:  # pragma: no cover - defensive server boundary
        LOG.exception("Metadata lookup failed")
        raise FastAPIHTTPException(status_code=400, detail=str(exc)) from exc


class SecopHTTPRequestHandler(BaseHTTPRequestHandler):
    """Handler HTTP pequeno usado por el servidor local del inspector."""
    server_version = "SECOPInspector/0.1"

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A003
        """Enviar los logs HTTP estandar al logger del modulo."""
        LOG.info("%s - %s", self.address_string(), format % args)

    def end_headers(self) -> None:  # noqa: D401
        """Agregar encabezados CORS permisivos antes de cerrar la respuesta."""
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Accept")
        self.send_header("Access-Control-Max-Age", "600")
        self.send_header("Access-Control-Expose-Headers", "Content-Disposition, Content-Type, Content-Length, X-File-Name")
        super().end_headers()

    @property
    def app(self) -> SecopApp:
        """Exponer la instancia de la app adjunta al servidor HTTP."""
        return self.server.app  # type: ignore[attr-defined]

    def do_OPTIONS(self) -> None:  # noqa: N802
        """Respond to preflight requests."""
        self.send_response(HTTPStatus.NO_CONTENT)
        self.end_headers()

    def do_GET(self) -> None:  # noqa: N802
        """Rutea las peticiones GET para la pagina HTML y las APIs JSON."""
        parsed = urlparse(self.path)
        if parsed.path == "/":
            self._send_html(_render_html_index())
            return
        if parsed.path == "/api/inspect":
            params = parse_qs(parsed.query)
            value = _first_non_empty(*(params.get("value", [])))
            if not value:
                self._send_json({"detail": "Missing 'value' query parameter."}, status=HTTPStatus.BAD_REQUEST)
                return
            try:
                result = self.app.inspect(value)
                payload = result.to_dict()
                payload["process_summary"] = _render_process_summary(result)
                payload["process_family_summaries"] = _render_process_family_summaries(result)
                self._send_json(payload)
            except Exception as exc:  # pragma: no cover - defensive server boundary
                LOG.exception("Inspection failed")
                self._send_json({"detail": str(exc)}, status=HTTPStatus.BAD_REQUEST)
            return
        if parsed.path == "/api/download":
            params = parse_qs(parsed.query)
            url = _first_non_empty(*(params.get("url", [])))
            filename = _first_non_empty(*(params.get("filename", [])))
            if not url:
                self._send_json({"detail": "Missing 'url' query parameter."}, status=HTTPStatus.BAD_REQUEST)
                return
            if not _is_allowed_download_url(url):
                self._send_json({"detail": "The requested URL is not allowed."}, status=HTTPStatus.BAD_REQUEST)
                return
            try:
                response = requests.get(
                    url,
                    headers={"User-Agent": USER_AGENT, "Accept": "*/*"},
                    timeout=DEFAULT_TIMEOUT,
                    stream=True,
                    allow_redirects=True,
                )
                response.raise_for_status()
                content_type = response.headers.get("Content-Type", "application/octet-stream")
                lower_content_type = content_type.lower()
                if "text/html" in lower_content_type or "application/xhtml" in lower_content_type:
                    raise ValueError(
                        "The SECOP URL returned HTML instead of a file. Open the official page and complete the manual step if the site asks for it."
                    )
                content = response.content
                safe_name = _first_non_empty(filename, Path(urlparse(url).path).name, "secop-document")
                safe_name = re.sub(r"[^A-Za-z0-9._-]+", "_", safe_name).strip("._-") or "secop-document"
                self._send_bytes(content, content_type=content_type, filename=safe_name)
            except Exception as exc:  # pragma: no cover - defensive server boundary
                LOG.exception("Download proxy failed")
                self._send_json({"detail": str(exc)}, status=HTTPStatus.BAD_REQUEST)
            return
        if parsed.path == "/api/metadata":
            params = parse_qs(parsed.query)
            dataset_id = _first_non_empty(*(params.get("dataset_id", [])))
            if not dataset_id:
                self._send_json({"detail": "Missing 'dataset_id' query parameter."}, status=HTTPStatus.BAD_REQUEST)
                return
            try:
                metadata = self.app.get_dataset_metadata(dataset_id)
                self._send_json(metadata.to_dict())
            except Exception as exc:  # pragma: no cover - defensive server boundary
                LOG.exception("Metadata lookup failed")
                self._send_json({"detail": str(exc)}, status=HTTPStatus.BAD_REQUEST)
            return

        self._send_json({"detail": "Not found."}, status=HTTPStatus.NOT_FOUND)

    def _send_html(self, content: str, status: HTTPStatus = HTTPStatus.OK) -> None:
        """Enviar una respuesta HTML con los encabezados y la codificacion correctos."""
        encoded = content.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def _send_json(self, payload: Any, status: HTTPStatus = HTTPStatus.OK) -> None:
        """Enviar una respuesta JSON usando el serializador seguro del modulo."""
        encoded = json.dumps(_json_safe(payload), ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def _send_bytes(self, content: bytes, *, content_type: str, filename: str, status: HTTPStatus = HTTPStatus.OK) -> None:
        """Enviar una respuesta binaria como adjunto con un nombre seguro."""
        encoded_filename = re.sub(r"[^A-Za-z0-9._-]+", "_", filename).strip("._-") or "secop-document"
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Content-Disposition", f'attachment; filename="{encoded_filename}"')
        self.send_header("X-File-Name", encoded_filename)
        self.end_headers()
        self.wfile.write(content)


class SecopHTTPServer(ThreadingHTTPServer):
    """Servidor HTTP con hilos que mantiene una instancia de SecopApp adjunta."""
    def __init__(self, server_address: Tuple[str, int], RequestHandlerClass: Any, app: SecopApp) -> None:
        super().__init__(server_address, RequestHandlerClass)
        self.app = app


def _print_human_result(result: InspectionResult) -> None:
    """Imprimir un resumen legible de la inspeccion en la terminal."""
    parsed = result.parsed_input
    print(f"Entrada: {parsed.raw_value}")
    print(f"Plataforma: {parsed.platform}")
    print(f"Tipo: {parsed.input_kind}")
    print(f"Identificador: {parsed.identifier}")
    if parsed.domain:
        print(f"Dominio: {parsed.domain}")
    if parsed.path:
        print(f"Ruta: {parsed.path}")
    if parsed.matched_parameters:
        print(f"Parametros: {', '.join(parsed.matched_parameters)}")
    print()
    print("Metadatos")
    for meta in result.metadata:
        print(f"- {meta.dataset_name} ({meta.dataset_id})")
        print(f"  Ultima actualizacion: {meta.last_update}")
        print(f"  Consultado: {meta.queried_at}")
    print()
    summary = _render_process_summary(result)
    if summary:
        print("Resumen de proceso")
        for key, value in summary.items():
            print(f"- {key}: {value}")
        print()
    print("Documentos")
    if result.document_groups:
        for source_group in result.document_groups:
            print(f"- {source_group['source_family']} ({source_group['document_count']} documentos)")
            for dataset_group in source_group.get("datasets", []):
                print(f"  - {dataset_group['dataset_name']} ({dataset_group['document_count']})")
                print(f"    Fuente del dataset: {dataset_group['dataset_source_url']}")
                for doc in dataset_group.get("documents", []):
                    print(f"    - {doc.get('title')}")
                    print(f"      Proceso: {doc.get('process_identifier')}")
                    print(f"      Archivo: {doc.get('file_name')}")
                    print(f"      URL: {doc.get('download_url') or 'no disponible'}")
    else:
        print("- Sin documentos relacionados.")
    if result.notes:
        print()
        print("Notas")
        for note in result.notes:
            print(f"- {note}")


def build_arg_parser() -> argparse.ArgumentParser:
    """Construir el parser CLI del inspector SECOP independiente."""
    parser = argparse.ArgumentParser(description="Inspector SECOP basado en datasets oficiales de datos.gov.co.")
    parser.add_argument("value", nargs="?", help="URL, referencia, constancia o identificador SECOP.")
    parser.add_argument("--json", action="store_true", help="Imprime el resultado como JSON.")
    parser.add_argument("--serve", action="store_true", help="Levanta el indice local en el navegador.")
    parser.add_argument("--host", default=DEFAULT_HOST, help="Host del servidor local.")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="Puerto del servidor local.")
    parser.add_argument("--no-open", action="store_true", help="No abrir el navegador automaticamente.")
    return parser


def _configure_stdio_utf8() -> None:
    """Forzar salida UTF-8 cuando el runtime permita reconfigurar los streams."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(encoding="utf-8", errors="replace")


def run_server(host: str, port: int, open_browser: bool = True) -> None:
    """Ejecutar el servidor local del inspector hasta que se interrumpa."""
    app = SecopApp()
    server = SecopHTTPServer((host, port), SecopHTTPRequestHandler, app)
    url = f"http://{host}:{port}/"
    LOG.info("SECOP inspector listening on %s", url)
    if open_browser:
        threading.Timer(0.5, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        LOG.info("Stopping server...")
    finally:
        server.shutdown()
        server.server_close()


def run_once(value: str, json_output: bool = False) -> int:
    """Ejecutar una inspeccion desde la CLI e imprimir el resultado."""
    app = SecopApp()
    result = app.inspect(value)
    if json_output:
        print(
            json.dumps(
                result.to_dict()
                | {
                    "process_summary": _render_process_summary(result),
                    "process_family_summaries": _render_process_family_summaries(result),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        _print_human_result(result)
    return 0


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Punto de entrada CLI para modo servidor e inspecciones puntuales."""
    _configure_stdio_utf8()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    if args.serve or not args.value:
        run_server(args.host, args.port, open_browser=not args.no_open)
        return 0

    return run_once(args.value, json_output=args.json)


if __name__ == "__main__":
    raise SystemExit(main())
