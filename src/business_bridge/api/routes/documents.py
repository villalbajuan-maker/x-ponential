from __future__ import annotations

import shutil
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile

from business_bridge.api.runtime import prepare_workspace
from business_bridge.api.schemas import (
    DocumentExtractionRecord,
    DocumentUploadResponse,
    MissingFieldAnswerRequest,
)
from business_bridge.core.audit import audit_event
from business_bridge.core import workspace
from business_bridge.services.document_service import (
    build_document_extraction_record as service_build_document_extraction_record,
    load_extraction_record as service_load_extraction_record,
    save_extraction_record as service_save_extraction_record,
    save_missing_field_answer as service_save_missing_field_answer,
)


router = APIRouter()


@router.post("/documents/upload", response_model=DocumentUploadResponse)
async def upload_document(file: UploadFile = File(...)) -> DocumentUploadResponse:
    """Guardar el archivo original sin modificar bajo un document_id unico."""

    prepare_workspace()

    if not file.filename:
        raise HTTPException(status_code=400, detail="Se requiere un nombre de archivo valido.")

    document_id = workspace.build_document_id()
    original_file_name = Path(file.filename).name
    stored_file_name = workspace.build_uploaded_filename(document_id, original_file_name)
    saved_path = workspace.ORIGINALS_DIR / stored_file_name

    with saved_path.open("wb") as destination:
        shutil.copyfileobj(file.file, destination)

    file_type = workspace.detect_file_type(original_file_name)
    audit_event(
        "document.uploaded",
        document_id,
        original_file_name=original_file_name,
        stored_file_name=stored_file_name,
        saved_to=str(saved_path),
        file_type=file_type,
        size_bytes=saved_path.stat().st_size,
    )

    return DocumentUploadResponse(
        status="ok",
        document_id=document_id,
        original_file_name=original_file_name,
        stored_file_name=stored_file_name,
        file_type=file_type,
        saved_to=str(saved_path),
        size_bytes=saved_path.stat().st_size,
    )


@router.post("/documents/{document_id}/process", response_model=DocumentExtractionRecord)
def process_document(document_id: str) -> DocumentExtractionRecord:
    """Ejecutar la extraccion para un documento cargado previamente."""

    prepare_workspace()
    audit_event("document.process.started", document_id)
    try:
        record = service_build_document_extraction_record(document_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    service_save_extraction_record(record)
    audit_event(
        "document.process.completed",
        document_id,
        detected_items=len(record.detected_items),
    )
    return record


@router.get("/documents/{document_id}/extraction", response_model=DocumentExtractionRecord)
def get_document_extraction(document_id: str) -> DocumentExtractionRecord:
    """Devolver el sidecar de extraccion guardado para un documento."""

    prepare_workspace()
    try:
        return service_load_extraction_record(document_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/documents/{document_id}/missing-answer", response_model=DocumentExtractionRecord)
def save_document_missing_answer(
    document_id: str,
    payload: MissingFieldAnswerRequest,
) -> DocumentExtractionRecord:
    """Guardar una respuesta faltante suministrada por el usuario."""

    prepare_workspace()
    try:
        return service_save_missing_field_answer(
            document_id,
            payload.field_key,
            payload.value,
            workspace.COMPANY_PROFILE_FILE,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
