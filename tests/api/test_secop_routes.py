from __future__ import annotations

import pytest
from fastapi import HTTPException as FastAPIHTTPException

from business_bridge.adapters.secop_constants import DATASETS, SECOP_DOWNLOAD_HOSTS
from business_bridge.adapters.secop_models import DatasetMetadataInfo, InspectionResult, ParsedSecopInput
from business_bridge.api.routes import secop as secop_routes


class FakeDownloadResponse:
    def __init__(self, *, content: bytes, content_type: str) -> None:
        self.content = content
        self.headers = {"Content-Type": content_type}

    def raise_for_status(self) -> None:
        return None


class FakeSecopService:
    def __init__(self, result: InspectionResult, metadata: DatasetMetadataInfo) -> None:
        self.result = result
        self.metadata = metadata
        self.inspect_calls: list[str] = []
        self.metadata_calls: list[str] = []

    def inspect(self, value: str) -> InspectionResult:
        self.inspect_calls.append(value)
        return self.result

    def get_dataset_metadata(self, dataset_id: str) -> DatasetMetadataInfo:
        self.metadata_calls.append(dataset_id)
        return self.metadata


def _inspection_result() -> InspectionResult:
    parsed_input = ParsedSecopInput(
        raw_value="CO1.NTC.1234567",
        input_kind="url",
        platform="secop_ii",
        identifier="CO1.NTC.1234567",
        original_url="https://community.secop.gov.co/Process/NoticeDetail?noticeUID=CO1.NTC.1234567",
        domain="community.secop.gov.co",
        path="/Process/NoticeDetail",
        matched_parameters=("noticeUID",),
        identifier_candidates=("CO1.NTC.1234567",),
    )
    metadata = [
        DatasetMetadataInfo(
            dataset_id=DATASETS["secop_ii_procesos"],
            dataset_name="Procesos SECOP II",
            queried_at="2026-07-12T00:00:00+00:00",
            last_update="2026-07-11T00:00:00+00:00",
            last_update_source="rowsUpdatedAt",
            source_url="https://example.com/secop-ii",
        )
    ]
    process_rows = [
        {
            "id_del_proceso": "CO1.NTC.1234567",
            "referencia_del_proceso": "REF-2",
            "entidad": "Entidad II",
            "nombre_del_procedimiento": "Obra II",
            "estado_del_procedimiento": "Abierto",
            "precio_base": "1000",
            "urlproceso": {"url": "https://example.com/proceso-ii"},
            "dataset_id": DATASETS["secop_ii_procesos"],
        }
    ]
    return InspectionResult(
        queried_at="2026-07-12T00:00:00+00:00",
        parsed_input=parsed_input,
        metadata=metadata,
        process_rows=process_rows,
        documents=[],
    )


def test_api_inspect_adds_summaries_and_metadata(monkeypatch: pytest.MonkeyPatch) -> None:
    result = _inspection_result()
    metadata = result.metadata[0]
    fake_service = FakeSecopService(result, metadata)
    monkeypatch.setattr(secop_routes, "secop_service", fake_service)

    payload = secop_routes.api_inspect("CO1.NTC.1234567")

    assert fake_service.inspect_calls == ["CO1.NTC.1234567"]
    assert payload["parsed_input"]["identifier"] == "CO1.NTC.1234567"
    assert payload["process_summary"]["process_id"] == "CO1.NTC.1234567"
    assert payload["process_family_summaries"][1]["source_family"] == "SECOP II"


def test_api_inspect_and_metadata_validation_errors() -> None:
    with pytest.raises(FastAPIHTTPException, match="Missing 'value'"):
        secop_routes.api_inspect("")

    with pytest.raises(FastAPIHTTPException, match="Missing 'dataset_id'"):
        secop_routes.api_metadata("")


def test_api_download_accepts_allowed_url_and_sanitizes_filename(monkeypatch: pytest.MonkeyPatch) -> None:
    allowed_url = f"https://{SECOP_DOWNLOAD_HOSTS[0]}/files/documento.pdf"
    download_response = FakeDownloadResponse(
        content=b"binary-data",
        content_type="application/pdf",
    )

    monkeypatch.setattr(
        secop_routes.requests,
        "get",
        lambda url, headers, timeout, stream, allow_redirects: download_response,
    )

    response = secop_routes.api_download(allowed_url, "../Contrato final (1).pdf")

    assert response.media_type == "application/pdf"
    assert response.headers["Content-Disposition"] == 'attachment; filename="Contrato_final_1_.pdf"'
    assert response.headers["X-File-Name"] == "Contrato_final_1_.pdf"


def test_api_download_rejects_disallowed_and_html_urls(monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(FastAPIHTTPException, match="not allowed"):
        secop_routes.api_download("https://malicious.example/file.pdf", "file.pdf")

    html_response = FakeDownloadResponse(
        content=b"<html></html>",
        content_type="text/html; charset=utf-8",
    )
    monkeypatch.setattr(
        secop_routes.requests,
        "get",
        lambda url, headers, timeout, stream, allow_redirects: html_response,
    )

    with pytest.raises(FastAPIHTTPException, match="returned HTML"):
        secop_routes.api_download(f"https://{SECOP_DOWNLOAD_HOSTS[0]}/files/documento.pdf", "file.pdf")
