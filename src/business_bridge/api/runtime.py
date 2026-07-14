from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import HTTPException

from business_bridge.api.schemas import DocumentExtractionRecord
from business_bridge.core.audit import audit_event
from business_bridge.core.observability import configure_logging
from business_bridge.core.company_profile import ensure_company_profile_file
from business_bridge.core import workspace
from business_bridge.services.document_service import load_extraction_record

from business_bridge.core.app_info import APP_NAME, APP_VERSION, CHECKPOINT  # noqa: F401


def prepare_workspace() -> None:
    """Preparar el workspace canonico antes de atender solicitudes."""

    workspace.ensure_company_layout()
    ensure_company_profile_file(workspace.COMPANY_PROFILE_FILE)


def load_document_extraction_or_404(document_id: str) -> DocumentExtractionRecord:
    """Cargar un registro de extraccion o convertir la ausencia en 404."""

    try:
        return load_extraction_record(document_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@asynccontextmanager
async def lifespan(app):
    configure_logging()
    prepare_workspace()
    audit_event("workspace.ready", "workspace", root=str(workspace.COMPANY_ROOT))
    yield
