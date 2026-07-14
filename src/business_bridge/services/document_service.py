from __future__ import annotations

import json
from pathlib import Path
from typing import Tuple

from fastapi import HTTPException

from business_bridge.adapters.ocr_detection import TENDER_EXPECTED_FIELDS, build_extraction_record
from business_bridge.adapters.ocr_text import clean_value as ocr_clean_value
from business_bridge.api.schemas import (
    DetectedItem,
    DocumentExtractionRecord,
    ReviewItemUpdateRequest,
)
from business_bridge.core.audit import audit_event
from business_bridge.core.company_profile import (
    COMPANY_PROFILE_FIELDS,
    load_company_profile_raw,
    save_company_profile,
)
from business_bridge.core.workspace import (
    COMPANY_PROFILE_FILE,
    find_uploaded_file,
    get_extraction_file_path,
)

REVIEW_STATUSES = {"pending_review", "accepted", "edited", "discarded"}
COMPANY_PROFILE_REVIEW_MAP = {
    "company.nit": "nit",
    "company.email": "email",
    "company.phone": "phone",
}
ALLOWED_MISSING_FIELD_KEYS = set(TENDER_EXPECTED_FIELDS) | COMPANY_PROFILE_FIELDS


def find_detected_item(record: DocumentExtractionRecord, item_id: str) -> Tuple[int, DetectedItem]:
    """Buscar un item detectado dentro de un registro por id."""

    for index, item in enumerate(record.detected_items):
        if item.item_id == item_id:
            return index, item
    raise HTTPException(status_code=404, detail=f"Detected item not found: {item_id}")


def build_document_extraction_record(document_id: str) -> DocumentExtractionRecord:
    """Construir el registro de extraccion que usa la pantalla de revision."""

    stored_file = find_uploaded_file(document_id)
    payload = build_extraction_record(stored_file, document_id)
    return DocumentExtractionRecord.model_validate(payload)


def save_extraction_record(record: DocumentExtractionRecord) -> Path:
    """Persistir el registro de extraccion como JSON sidecar."""

    path = get_extraction_file_path(record.document_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(record.model_dump(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    audit_event(
        "document.extraction_saved",
        record.document_id,
        saved_to=str(path),
        detected_items=len(record.detected_items),
    )
    return path


def load_extraction_record(document_id: str) -> DocumentExtractionRecord:
    """Cargar desde disco un registro de extraccion guardado previamente."""

    path = get_extraction_file_path(document_id)
    if not path.exists():
        raise FileNotFoundError(f"Extraction not found for document: {document_id}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    return DocumentExtractionRecord.model_validate(payload)


def save_missing_field_answer(
    document_id: str,
    field_key: str,
    value: str,
    profile_file: Path = COMPANY_PROFILE_FILE,
) -> DocumentExtractionRecord:
    """Guardar una respuesta faltante y promoverla si el campo es reutilizable."""

    normalized_field_key = field_key.strip()
    cleaned_value = ocr_clean_value(value)

    if not normalized_field_key:
        raise HTTPException(status_code=400, detail="Field key is required.")
    if normalized_field_key not in ALLOWED_MISSING_FIELD_KEYS:
        raise HTTPException(
            status_code=400, detail="The requested field is not supported by this flow."
        )
    if not cleaned_value:
        raise HTTPException(status_code=400, detail="A non-empty answer is required.")

    record = load_extraction_record(document_id)
    record.supplemental_answers[normalized_field_key] = cleaned_value

    if normalized_field_key in COMPANY_PROFILE_FIELDS:
        current_profile = load_company_profile_raw(profile_file)
        current_profile[normalized_field_key] = cleaned_value
        save_company_profile(profile_file, current_profile)
        audit_event(
            "company_profile.answer_promoted",
            document_id,
            field_key=normalized_field_key,
            profile_file=str(profile_file),
        )

    save_extraction_record(record)
    audit_event(
        "document.missing_answer_saved",
        document_id,
        field_key=normalized_field_key,
    )
    return record


def update_reviewed_item(
    document_id: str,
    payload: ReviewItemUpdateRequest,
    profile_file: Path = COMPANY_PROFILE_FILE,
) -> DocumentExtractionRecord:
    """Aplicar una decision humana de revision a un item detectado."""

    record = load_extraction_record(document_id)
    item_index, detected_item = find_detected_item(record, payload.item_id)
    normalized_status = payload.status.strip().lower()

    if normalized_status not in REVIEW_STATUSES - {"pending_review"}:
        raise HTTPException(
            status_code=400,
            detail="El estado debe ser accepted, edited o discarded.",
        )

    updated_value = ocr_clean_value(payload.value) if payload.value is not None else ""
    if normalized_status == "edited" and not updated_value:
        raise HTTPException(
            status_code=400, detail="Los items editados requieren un valor no vacio."
        )

    if normalized_status in {"accepted", "edited"} and updated_value:
        detected_item.value = updated_value
    detected_item.status = normalized_status
    record.detected_items[item_index] = detected_item

    if payload.save_to_company_profile:
        if normalized_status not in {"accepted", "edited"}:
            raise HTTPException(
                status_code=400,
                detail="Only accepted or edited items can be saved to the company profile.",
            )
        profile_key = COMPANY_PROFILE_REVIEW_MAP.get(detected_item.field_key)
        if not profile_key or not detected_item.reusable:
            raise HTTPException(
                status_code=400,
                detail="Only reusable company fields can be saved to the company profile.",
            )
        if not detected_item.value:
            raise HTTPException(
                status_code=400,
                detail="The selected item does not have a value to save to the company profile.",
            )
        current_profile = load_company_profile_raw(profile_file)
        current_profile[profile_key] = detected_item.value
        save_company_profile(profile_file, current_profile)
        audit_event(
            "company_profile.review_promoted",
            document_id,
            item_id=detected_item.item_id,
            profile_key=profile_key,
        )

    save_extraction_record(record)
    audit_event(
        "document.review_item_updated",
        document_id,
        item_id=payload.item_id,
        status=normalized_status,
    )
    return record
