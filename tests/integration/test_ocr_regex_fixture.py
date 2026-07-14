from __future__ import annotations

from pathlib import Path

from business_bridge.adapters.ocr import extract_regex_items


FIXTURE_PATH = Path(__file__).resolve().parents[1] / "fixtures" / "documents" / "tender_sample.txt"


def test_extract_regex_items_from_semi_real_tender_fixture() -> None:
    page_text = FIXTURE_PATH.read_text(encoding="utf-8")

    items = extract_regex_items([page_text])
    items_by_field = {item["field_key"]: item for item in items}

    assert items_by_field["company.nit"]["value"] == "901.234.567-8"
    assert items_by_field["company.email"]["value"] == "contacto@businessbridge.co"
    assert items_by_field["company.phone"]["value"] == "+57 300 123 4567"
    assert items_by_field["tender.process_number"]["value"] == "LP-2026-001"
    assert items_by_field["tender.entity"]["value"] == "Alcaldia de Bogota"
    assert items_by_field["tender.offer_value"]["value"] == "COP $12.345.678"
    assert items_by_field["tender.execution_term"]["value"] == "90 dias"
    assert items_by_field["tender.date"]["value"] == "10/07/2026"
