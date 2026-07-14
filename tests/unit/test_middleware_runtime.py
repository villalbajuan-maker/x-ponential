from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest
from fastapi import HTTPException, Response
from starlette.requests import Request

from business_bridge.api import middleware as middleware_module
from business_bridge.api import runtime as runtime_module
from business_bridge.core import workspace as workspace_module


def _make_request(
    *,
    method: str = "GET",
    path: str = "/documents/doc_1/process",
    headers: list[tuple[bytes, bytes]] | None = None,
) -> Request:
    async def receive() -> dict[str, object]:
        return {"type": "http.request", "body": b"", "more_body": False}

    scope = {
        "type": "http",
        "method": method,
        "path": path,
        "headers": headers or [],
        "client": ("127.0.0.1", 1234),
        "query_string": b"",
        "scheme": "http",
        "server": ("testserver", 80),
    }
    return Request(scope, receive)


def test_request_audit_middleware_sets_headers(monkeypatch: pytest.MonkeyPatch) -> None:
    request = _make_request(
        headers=[
            (b"x-request-id", b"req-123"),
            (b"x-operation-id", b"op-456"),
            (b"user-agent", b"pytest"),
        ]
    )

    async def call_next(current_request: Request) -> Response:
        return Response("ok", status_code=200)

    response = asyncio.run(middleware_module.request_audit_middleware(request, call_next))

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "req-123"
    assert response.headers["X-Operation-ID"] == "op-456"


def test_request_audit_middleware_logs_failures(monkeypatch: pytest.MonkeyPatch) -> None:
    request = _make_request()
    events: list[tuple[int, str, str, dict[str, object]]] = []
    monkeypatch.setattr(
        middleware_module,
        "log_event",
        lambda level, action, subject, **details: events.append((level, action, subject, details)),
    )

    async def call_next(current_request: Request) -> Response:
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError):
        asyncio.run(middleware_module.request_audit_middleware(request, call_next))

    assert any(action == "request.failed" for _, action, _, _ in events)


def test_prepare_workspace_and_runtime_lifespan(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    company_root = tmp_path / "company" / "Business_Bridge"
    originals_dir = company_root / "originales"
    actualizados_dir = company_root / "actualizados"
    profile_file = company_root / "data.json"

    monkeypatch.setattr(workspace_module, "COMPANY_ROOT", company_root)
    monkeypatch.setattr(workspace_module, "ORIGINALS_DIR", originals_dir)
    monkeypatch.setattr(workspace_module, "ACTUALIZADOS_DIR", actualizados_dir)
    monkeypatch.setattr(workspace_module, "COMPANY_PROFILE_FILE", profile_file)
    monkeypatch.setattr(runtime_module.workspace, "COMPANY_ROOT", company_root)
    monkeypatch.setattr(runtime_module.workspace, "ORIGINALS_DIR", originals_dir)
    monkeypatch.setattr(runtime_module.workspace, "ACTUALIZADOS_DIR", actualizados_dir)
    monkeypatch.setattr(runtime_module.workspace, "COMPANY_PROFILE_FILE", profile_file)

    runtime_module.prepare_workspace()

    assert company_root.exists()
    assert originals_dir.exists()
    assert actualizados_dir.exists()
    assert profile_file.exists()

    calls: list[str] = []
    monkeypatch.setattr(runtime_module, "configure_logging", lambda: calls.append("logging"))
    monkeypatch.setattr(runtime_module, "prepare_workspace", lambda: calls.append("workspace"))
    monkeypatch.setattr(
        runtime_module,
        "audit_event",
        lambda action, subject, **details: calls.append(f"{action}:{subject}"),
    )

    async def run_lifespan() -> None:
        async with runtime_module.lifespan(SimpleNamespace()):
            calls.append("inside")

    asyncio.run(run_lifespan())

    assert calls == ["logging", "workspace", "workspace.ready:workspace", "inside"]


def test_load_document_extraction_or_404(monkeypatch: pytest.MonkeyPatch) -> None:
    sentinel = SimpleNamespace(document_id="doc-1")
    monkeypatch.setattr(
        runtime_module,
        "load_extraction_record",
        lambda document_id: sentinel,
    )

    assert runtime_module.load_document_extraction_or_404("doc-1") is sentinel

    def raise_missing(document_id: str):
        raise FileNotFoundError("missing")

    monkeypatch.setattr(runtime_module, "load_extraction_record", raise_missing)

    with pytest.raises(HTTPException, match="missing"):
        runtime_module.load_document_extraction_or_404("doc-1")
