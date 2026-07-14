from __future__ import annotations

from pathlib import Path

from business_bridge.adapters.ocr_detection import (
    add_detected_item,
    build_extraction_record,
    calculate_overall_confidence,
    clean_extracted_pages,
)


def test_add_detected_item_filters_short_values_and_duplicates() -> None:
    items: list[dict[str, object]] = []
    seen_values: set[tuple[str, str]] = set()

    add_detected_item(items, seen_values, "company.phone", "Telefono", "+57 300 123 4567", 0.91, 1)
    add_detected_item(items, seen_values, "company.phone", "Telefono", "valor 300 123 4567", 0.91, 1)
    add_detected_item(items, seen_values, "company.phone", "Telefono", "3001234", 0.91, 1)
    add_detected_item(items, seen_values, "company.nit", "NIT", "1234", 0.95, 1)
    add_detected_item(items, seen_values, "tender.process_number", "Proceso", "LP", 0.88, 1)
    add_detected_item(items, seen_values, "tender.process_number", "Proceso", "LP-2026-001", 0.88, 1)
    add_detected_item(items, seen_values, "company.nit", "NIT", "901.234.567-8", 0.95, 1, reusable=True)
    add_detected_item(items, seen_values, "company.nit", "NIT", "901.234.567-8", 0.95, 1, reusable=True)

    assert [item["field_key"] for item in items] == [
        "company.phone",
        "tender.process_number",
        "company.nit",
    ]
    assert items[0]["value"] == "+57 300 123 4567"
    assert items[2]["reusable"] is True


def test_clean_pages_confidence_and_build_extraction_record(monkeypatch) -> None:
    monkeypatch.setattr(
        "business_bridge.adapters.ocr_detection.extract_text_from_file",
        lambda stored_file: (["  NIT 901.234.567-8  "], "txt", "txt", []),
    )
    monkeypatch.setattr(
        "business_bridge.adapters.ocr_detection.extract_regex_items",
        lambda page_texts: [
            {
                "field_key": "company.nit",
                "confidence": 0.95,
            }
        ],
    )

    record = build_extraction_record(Path("doc_123__sample.txt"), "doc_123")

    assert clean_extracted_pages(["  hola  ", "linea-\ncontinua"]) == ["hola", "lineacontinua"]
    assert calculate_overall_confidence([{"confidence": 0.9}, {"confidence": 0.8}], "pdf_scanned", "texto") == 0.8
    assert calculate_overall_confidence([], "image", "texto") == 0.45
    assert calculate_overall_confidence([], "txt", "") == 0.0
    assert record["document_id"] == "doc_123"
    assert record["file_name"] == "sample.txt"
    assert record["raw_text_preview"] == "NIT 901.234.567-8"
    assert "company.nit" not in record["missing_fields"]
    assert record["confidence"] == 0.95


def test_build_extraction_record_adds_warning_when_text_is_missing(monkeypatch) -> None:
    monkeypatch.setattr(
        "business_bridge.adapters.ocr_detection.extract_text_from_file",
        lambda stored_file: ([""], "pdf", "pdf_scanned", []),
    )
    monkeypatch.setattr(
        "business_bridge.adapters.ocr_detection.extract_regex_items",
        lambda page_texts: [],
    )

    record = build_extraction_record(Path("doc_999__sample.pdf"))

    assert record["document_id"] == "doc_999"
    assert record["file_type"] == "pdf"
    assert record["document_type"] == "pdf_scanned"
    assert record["warnings"] == ["No text could be extracted from the document."]
    assert record["confidence"] == 0.0
