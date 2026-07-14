from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from business_bridge.core.workspace import load_index_html


router = APIRouter()


@router.get("/", response_class=HTMLResponse)
def root() -> HTMLResponse:
    """Servir el frontend HTML del piloto."""

    return HTMLResponse(content=load_index_html())
