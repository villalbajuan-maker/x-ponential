from __future__ import annotations

import logging
from typing import Any, Dict

from business_bridge.core.observability import build_event, emit_event

LOG = logging.getLogger("business_bridge.audit")


def audit_event(action: str, subject: str, **details: Any) -> Dict[str, Any]:
    """Construir y registrar un evento de auditoria estructurado."""

    return emit_event(LOG, logging.INFO, build_event(action, subject, **details))


def log_event(level: int, action: str, subject: str, **details: Any) -> Dict[str, Any]:
    """Emitir un evento estructurado con el nivel de logging indicado."""

    return emit_event(LOG, level, build_event(action, subject, **details))
