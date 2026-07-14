from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Generator

import pytest
from fastapi.testclient import TestClient

import business_bridge.api.main as main_module
from business_bridge.core import workspace as workspace_module


FIXTURES_DIR = Path(__file__).resolve().parents[1] / "fixtures"
DOCUMENT_FIXTURE_PATH = FIXTURES_DIR / "documents" / "tender_sample.txt"
PROFILE_IMPORT_FIXTURE_PATH = FIXTURES_DIR / "company_profile" / "import_payload.json"
DOCUMENT_TEXT = DOCUMENT_FIXTURE_PATH.read_text(encoding="utf-8")
PROFILE_IMPORT_PAYLOAD = json.loads(PROFILE_IMPORT_FIXTURE_PATH.read_text(encoding="utf-8"))


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Generator[TestClient, None, None]:
    company_root = tmp_path / "company" / "Business_Bridge"
    originals_dir = company_root / "originales"
    actualizados_dir = company_root / "actualizados"
    profile_file = company_root / "data.json"

    for path in (company_root, originals_dir, actualizados_dir):
        path.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(workspace_module, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(workspace_module, "COMPANY_ROOT", company_root)
    monkeypatch.setattr(workspace_module, "ORIGINALS_DIR", originals_dir)
    monkeypatch.setattr(workspace_module, "ACTUALIZADOS_DIR", actualizados_dir)
    monkeypatch.setattr(workspace_module, "COMPANY_PROFILE_FILE", profile_file)
    monkeypatch.setattr(main_module, "COMPANY_ROOT", company_root)
    monkeypatch.setattr(main_module, "ORIGINALS_DIR", originals_dir)
    monkeypatch.setattr(main_module, "COMPANY_PROFILE_FILE", profile_file)

    with TestClient(main_module.app) as test_client:
        yield test_client


@pytest.fixture()
def uploaded_document(client: TestClient) -> dict[str, Any]:
    response = client.post(
        "/documents/upload",
        files={"file": ("tender_sample.txt", DOCUMENT_TEXT.encode("utf-8"), "text/plain")},
    )
    assert response.status_code == 200
    return response.json()


@pytest.fixture()
def processed_document(client: TestClient, uploaded_document: dict[str, Any]) -> dict[str, Any]:
    document_id = str(uploaded_document["document_id"])

    response = client.post(f"/documents/{document_id}/process")
    assert response.status_code == 200
    process_data = response.json()
    assert process_data["document_id"] == document_id
    return process_data


def _find_item_by_field(process_data: dict[str, Any], field_key: str) -> dict[str, Any]:
    return next(item for item in process_data["detected_items"] if item["field_key"] == field_key)


def _find_item_by_id(process_data: dict[str, Any], item_id: str) -> dict[str, Any]:
    return next(item for item in process_data["detected_items"] if item["item_id"] == item_id)


def test_root_serves_the_business_bridge_ui(client: TestClient) -> None:
    root_response = client.get("/")

    assert root_response.status_code == 200
    assert "Business Bridge" in root_response.text


def test_health_reports_workspace_ready(client: TestClient) -> None:
    health_response = client.get("/health")

    assert health_response.status_code == 200
    assert health_response.json()["app_name"] == "Business Bridge"
    assert health_response.json()["company_ready"] is True


def test_company_profile_read_returns_default_profile(client: TestClient) -> None:
    profile_response = client.get("/company-profile")

    assert profile_response.status_code == 200
    assert profile_response.json()["company_profile"]["business_name"] == ""


def test_company_profile_update_persists_payload(client: TestClient) -> None:
    update_response = client.post(
        "/company-profile/update",
        json={"business_name": "Business Bridge SAS", "city": "Bogota"},
    )

    assert update_response.status_code == 200
    assert update_response.json()["company_profile"]["business_name"] == "Business Bridge SAS"

    profile_response = client.get("/company-profile")
    assert profile_response.json()["company_profile"]["city"] == "Bogota"


def test_company_profile_import_accepts_nested_payload(client: TestClient) -> None:
    import_response = client.post(
        "/company-profile/import",
        files={
            "file": (
                "import_payload.json",
                json.dumps(PROFILE_IMPORT_PAYLOAD).encode("utf-8"),
                "application/json",
            )
        },
    )

    assert import_response.status_code == 200
    import_data = import_response.json()
    assert import_data["company_profile"]["business_name"] == "Business Bridge SAS"
    assert import_data["company_profile"]["email"] == "hello@businessbridge.co"
    assert import_data["company_profile"]["nit"] == "901234567-8"
    assert "business_name" in import_data["imported_keys"]
    assert "email" in import_data["imported_keys"]
    assert "nit" in import_data["imported_keys"]
    assert "city" in import_data["imported_keys"]

    profile_response = client.get("/company-profile")
    assert profile_response.json()["company_profile"]["business_name"] == "Business Bridge SAS"


def test_document_upload_returns_safe_stored_name(uploaded_document: dict[str, Any]) -> None:
    assert uploaded_document["original_file_name"] == "tender_sample.txt"
    assert uploaded_document["stored_file_name"].startswith(uploaded_document["document_id"])
    assert uploaded_document["file_type"] == "txt"
    assert uploaded_document["size_bytes"] > 0


def test_document_upload_emits_correlated_structured_logs(
    client: TestClient, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.INFO, logger="business_bridge.audit")

    response = client.post(
        "/documents/upload",
        files={"file": ("tender_sample.txt", DOCUMENT_TEXT.encode("utf-8"), "text/plain")},
    )

    assert response.status_code == 200
    request_id = response.headers["X-Request-ID"]
    assert request_id
    assert response.headers["X-Operation-ID"] == request_id

    events = [
        json.loads(record.getMessage())
        for record in caplog.records
        if record.name == "business_bridge.audit"
    ]
    correlated_events = [event for event in events if event["request_id"] == request_id]

    assert any(event["action"] == "request.started" for event in correlated_events)
    assert any(event["action"] == "document.uploaded" for event in correlated_events)
    assert any(
        event["action"] == "request.completed" and event["details"]["status_code"] == 200
        for event in correlated_events
    )


def test_document_process_and_extraction_endpoints_persist_record(
    client: TestClient,
    processed_document: dict[str, Any],
) -> None:
    document_id = str(processed_document["document_id"])

    assert processed_document["detected_items"]

    extraction_response = client.get(f"/documents/{document_id}/extraction")

    assert extraction_response.status_code == 200
    assert extraction_response.json()["document_id"] == document_id


def test_review_endpoint_returns_processed_record(
    client: TestClient,
    processed_document: dict[str, Any],
) -> None:
    document_id = str(processed_document["document_id"])

    review_response = client.get(f"/review/{document_id}")

    assert review_response.status_code == 200
    assert review_response.json()["document_id"] == document_id


def test_review_update_promotes_nit_to_company_profile(
    client: TestClient,
    processed_document: dict[str, Any],
) -> None:
    document_id = str(processed_document["document_id"])
    nit_item = _find_item_by_field(processed_document, "company.nit")

    review_response = client.post(
        f"/review/{document_id}/update-item",
        json={
            "item_id": nit_item["item_id"],
            "status": "accepted",
            "save_to_company_profile": True,
        },
    )

    assert review_response.status_code == 200
    reviewed_nit = _find_item_by_id(review_response.json(), nit_item["item_id"])
    assert reviewed_nit["status"] == "accepted"

    profile_response = client.get("/company-profile")
    assert profile_response.json()["company_profile"]["nit"] == nit_item["value"]


def test_missing_answer_saves_phone_answer_and_promotes_profile(
    client: TestClient,
    processed_document: dict[str, Any],
) -> None:
    document_id = str(processed_document["document_id"])

    missing_answer_response = client.post(
        f"/documents/{document_id}/missing-answer",
        json={"field_key": "phone", "value": "+57 300 765 4321"},
    )

    assert missing_answer_response.status_code == 200
    assert missing_answer_response.json()["supplemental_answers"]["phone"] == "+57 300 765 4321"

    profile_response = client.get("/company-profile")
    assert profile_response.json()["company_profile"]["phone"] == "+57 300 765 4321"
