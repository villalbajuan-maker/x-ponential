from __future__ import annotations

import re
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, cast
from urllib.parse import parse_qs, urlparse

from business_bridge.adapters.secop_constants import (
    SECOP_DOWNLOAD_HOSTS,
    SEARCH_MAX_TOKENS,
    SEARCH_MIN_TOKEN_LENGTH,
)


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
            elif len(token) < SEARCH_MIN_TOKEN_LENGTH and token not in {
                "dane",
                "geih",
                "secop",
                "co1",
                "ntc",
                "req",
            }:
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
    return any(
        hostname.endswith(f".{allowed}") for allowed in SECOP_DOWNLOAD_HOSTS if "." in allowed
    )


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
        return _json_safe(asdict(cast(Any, value)))
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    return value
