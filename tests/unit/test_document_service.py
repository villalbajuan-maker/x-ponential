from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from fastapi import HTTPException

from business_bridge.api.schemas import (
    DetectedItem,
    DocumentExtractionRecord,
    ReviewItemUpdateRequest,
)
from business_bridge.core.company_profile import (
    ensure_company_profile_file,
    load_company_profile_raw,
)
from business_bridge.core import workspace as workspace_module
from business_bridge.services.document_service import (
    build_document_extraction_record,
    find_detected_item,
    load_extraction_record,
    save_extraction_record,
    save_missing_field_answer,
    update_reviewed_item,
)


SAMPLE_DOCUMENT_LINES = [
    "NIT 901.234.567-8",
    "contacto@businessbridge.co",
    "+57 300 123 4567",
    "LP-2026-001",
    "Alcaldia de Bogota",
    "90 dias",
    "10/07/2026",
]


@pytest.fixture()
def document_workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    originals_dir = tmp_path / "originales"
    actualizados_dir = tmp_path / "actualizados"
    originals_dir.mkdir()
    actualizados_dir.mkdir()

    monkeypatch.setattr(workspace_module, "ORIGINALS_DIR", originals_dir)
    monkeypatch.setattr(workspace_module, "ACTUALIZADOS_DIR", actualizados_dir)

    document_id = "doc_test"
    stored_file = originals_dir / f"{document_id}__sample.txt"
    stored_file.write_text("\n".join(SAMPLE_DOCUMENT_LINES), encoding="utf-8")

    profile_file = tmp_path / "data.json"
    ensure_company_profile_file(profile_file)

    return {
        "document_id": document_id,
        "profile_file": profile_file,
    }


def test_find_detected_item_returns_index_and_item() -> None:
    record = DocumentExtractionRecord(
        document_id="doc_test",
        file_name="sample.txt",
        file_type="txt",
        document_type="txt",
        confidence=0.9,
        raw_text_preview="NIT 901.234.567-8",
        detected_items=[
            DetectedItem(
                item_id="item-1",
                field_key="company.nit",
                label="NIT",
                value="901.234.567-8",
                confidence=0.99,
                source="regex",
                reusable=True,
            )
        ],
        missing_fields=[],
        warnings=[],
    )

    index, detected_item = find_detected_item(record, "item-1")

    assert index == 0
    assert detected_item.field_key == "company.nit"


def test_find_detected_item_raises_for_missing_item() -> None:
    record = DocumentExtractionRecord(
        document_id="doc_test",
        file_name="sample.txt",
        file_type="txt",
        document_type="txt",
        confidence=0.9,
        raw_text_preview="NIT 901.234.567-8",
        detected_items=[],
        missing_fields=[],
        warnings=[],
    )

    with pytest.raises(HTTPException, match="Detected item not found"):
        find_detected_item(record, "missing")


def test_build_document_extraction_record_reads_uploaded_file(
    document_workspace: dict[str, Any],
) -> None:
    record = build_document_extraction_record(document_workspace["document_id"])

    assert record.document_id == document_workspace["document_id"]
    assert record.file_name == "sample.txt"
    assert record.detected_items


def test_save_and_load_extraction_record_roundtrip(
    document_workspace: dict[str, Any],
) -> None:
    record = build_document_extraction_record(document_workspace["document_id"])

    saved_path = save_extraction_record(record)
    reloaded = load_extraction_record(document_workspace["document_id"])

    assert saved_path.exists()
    assert reloaded.document_id == document_workspace["document_id"]
    assert reloaded.detected_items


def test_update_reviewed_item_promotes_company_profile(
    document_workspace: dict[str, Any],
) -> None:
    record = build_document_extraction_record(document_workspace["document_id"])
    save_extraction_record(record)
    nit_item = next(item for item in record.detected_items if item.field_key == "company.nit")

    updated = update_reviewed_item(
        document_workspace["document_id"],
        ReviewItemUpdateRequest(
            item_id=nit_item.item_id,
            status="accepted",
            save_to_company_profile=True,
        ),
        profile_file=document_workspace["profile_file"],
    )

    reviewed_nit = next(item for item in updated.detected_items if item.item_id == nit_item.item_id)
    assert reviewed_nit.status == "accepted"
    assert load_company_profile_raw(document_workspace["profile_file"])["nit"] == nit_item.value


def test_save_missing_field_answer_promotes_company_profile(
    document_workspace: dict[str, Any],
) -> None:
    record = build_document_extraction_record(document_workspace["document_id"])
    save_extraction_record(record)

    missing_answer = save_missing_field_answer(
        document_workspace["document_id"],
        "phone",
        "+57 300 765 4321",
        profile_file=document_workspace["profile_file"],
    )

    assert missing_answer.supplemental_answers["phone"] == "+57 300 765 4321"
    assert (
        load_company_profile_raw(document_workspace["profile_file"])["phone"] == "+57 300 765 4321"
    )


def test_load_extraction_record_missing_file_raises(document_workspace: dict[str, Any]) -> None:
    with pytest.raises(FileNotFoundError, match="Extraction not found"):
        load_extraction_record(document_workspace["document_id"])


@pytest.mark.parametrize(
    ("field_key", "value", "expected_message"),
    [
        ("", "123", "Field key is required"),
        ("unsupported.field", "123", "not supported"),
        ("phone", "   ", "non-empty answer"),
    ],
)
def test_save_missing_field_answer_rejects_invalid_inputs(
    document_workspace: dict[str, Any],
    field_key: str,
    value: str,
    expected_message: str,
) -> None:
    with pytest.raises(HTTPException, match=expected_message):
        save_missing_field_answer(
            document_workspace["document_id"],
            field_key,
            value,
            profile_file=document_workspace["profile_file"],
        )


def test_update_reviewed_item_rejects_invalid_status_and_nonreusable_profile_save(
    document_workspace: dict[str, Any],
) -> None:
    record = build_document_extraction_record(document_workspace["document_id"])
    save_extraction_record(record)
    process_item = next(
        item for item in record.detected_items if item.field_key == "tender.process_number"
    )

    with pytest.raises(HTTPException, match="accepted, edited o discarded"):
        update_reviewed_item(
            document_workspace["document_id"],
            ReviewItemUpdateRequest(item_id=process_item.item_id, status="pending_review"),
            profile_file=document_workspace["profile_file"],
        )

    with pytest.raises(HTTPException, match="requieren un valor no vacio"):
        update_reviewed_item(
            document_workspace["document_id"],
            ReviewItemUpdateRequest(item_id=process_item.item_id, status="edited"),
            profile_file=document_workspace["profile_file"],
        )

    with pytest.raises(HTTPException, match="Only reusable company fields"):
        update_reviewed_item(
            document_workspace["document_id"],
            ReviewItemUpdateRequest(
                item_id=process_item.item_id,
                status="accepted",
                save_to_company_profile=True,
            ),
            profile_file=document_workspace["profile_file"],
        )
