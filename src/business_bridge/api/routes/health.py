from __future__ import annotations

from fastapi import APIRouter

from business_bridge.api.runtime import CHECKPOINT, APP_NAME, APP_VERSION
from business_bridge.api.schemas import HealthResponse
from business_bridge.core.workspace import company_layout_is_ready


router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """Reportar si Business Bridge esta listo para servir peticiones."""

    return HealthResponse(
        status="ok",
        app_name=APP_NAME,
        version=APP_VERSION,
        checkpoint=CHECKPOINT,
        company_ready=company_layout_is_ready(),
    )
