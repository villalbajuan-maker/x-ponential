from __future__ import annotations

import json
import logging
import uuid
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any, Dict, Iterator

from business_bridge.core.app_info import (
    APP_NAME,
    APP_VERSION,
    CHECKPOINT,
    LOG_SCHEMA_VERSION,
    SERVICE_NAME,
)

LOG = logging.getLogger("business_bridge.audit")

_DEFAULT_CONTEXT: Dict[str, Any] = {
    "request_id": "system",
    "operation_id": "system",
    "method": None,
    "path": None,
    "route": None,
}
_REQUEST_CONTEXT: ContextVar[Dict[str, Any] | None] = ContextVar(
    "business_bridge_request_context", default=None
)


def configure_logging(level: int = logging.INFO) -> None:
    """Ajustar el nivel base de logging para que los eventos estructurados no se pierdan."""

    logging.getLogger().setLevel(level)


def generate_request_id() -> str:
    """Generar un identificador corto para correlacionar una request."""

    return uuid.uuid4().hex


def current_context() -> Dict[str, Any]:
    """Obtener el contexto activo de observabilidad."""

    context = dict(_DEFAULT_CONTEXT)
    stored = _REQUEST_CONTEXT.get()
    if stored:
        context.update({key: value for key, value in stored.items() if value is not None})
    if not context.get("operation_id"):
        context["operation_id"] = context["request_id"]
    return context


@contextmanager
def request_context(**values: Any) -> Iterator[Dict[str, Any]]:
    """Vincular contexto de request durante un bloque de ejecucion."""

    context = current_context()
    for key, value in values.items():
        if value is not None:
            context[key] = value
    if not context.get("operation_id"):
        context["operation_id"] = context["request_id"]
    token = _REQUEST_CONTEXT.set(context)
    try:
        yield context
    finally:
        _REQUEST_CONTEXT.reset(token)


def build_event(action: str, subject: str, **details: Any) -> Dict[str, Any]:
    """Construir un evento JSON con metadatos de contexto y version actual."""

    context = current_context()
    clean_details = {key: value for key, value in details.items() if value is not None}
    return {
        "schema_version": LOG_SCHEMA_VERSION,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "service": SERVICE_NAME,
        "app_name": APP_NAME,
        "app_version": APP_VERSION,
        "checkpoint": CHECKPOINT,
        "request_id": context["request_id"],
        "operation_id": context["operation_id"],
        "method": context.get("method"),
        "path": context.get("path"),
        "route": context.get("route"),
        "action": action,
        "subject": subject,
        "details": clean_details,
    }


def emit_event(logger: logging.Logger, level: int, event: Dict[str, Any]) -> Dict[str, Any]:
    """Emitir un evento estructurado como una sola linea JSON."""

    logger.log(level, json.dumps(event, ensure_ascii=False, sort_keys=True))
    return event
