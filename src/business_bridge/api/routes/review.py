from __future__ import annotations

from fastapi import APIRouter, HTTPException

from business_bridge.api.runtime import load_document_extraction_or_404, prepare_workspace
from business_bridge.api.schemas import DocumentExtractionRecord, ReviewItemUpdateRequest
from business_bridge.core import workspace
from business_bridge.services.document_service import update_reviewed_item as service_update_reviewed_item


router = APIRouter()


@router.get("/review/{document_id}", response_model=DocumentExtractionRecord)
def get_review(document_id: str) -> DocumentExtractionRecord:
    """Devolver el registro de extraccion usado por la pantalla de revision."""

    prepare_workspace()
    return load_document_extraction_or_404(document_id)


@router.post("/review/{document_id}/update-item", response_model=DocumentExtractionRecord)
def update_review_item(
    document_id: str,
    payload: ReviewItemUpdateRequest,
) -> DocumentExtractionRecord:
    """Actualizar el estado o el valor de un item revisado."""

    prepare_workspace()
    try:
        return service_update_reviewed_item(document_id, payload, workspace.COMPANY_PROFILE_FILE)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
