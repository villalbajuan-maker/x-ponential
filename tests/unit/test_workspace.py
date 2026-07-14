from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from fastapi import HTTPException

from business_bridge.core.workspace import (
    build_document_id,
    build_uploaded_filename,
    company_layout_is_ready,
    decode_uploaded_json,
    ensure_company_layout,
    find_uploaded_file,
    load_index_html,
    normalize_uploaded_filename,
)


def test_workspace_builders_keep_filenames_safe() -> None:
    assert normalize_uploaded_filename("../Factura Final 2026.pdf") == "Factura_Final_2026.pdf"
    assert (
        build_uploaded_filename("doc_abc", "../Factura Final 2026.pdf")
        == "doc_abc__Factura_Final_2026.pdf"
    )
    assert build_document_id().startswith("doc_")


def test_load_index_html_uses_fallback_when_missing(tmp_path: Path) -> None:
    missing_index = tmp_path / "index.html"

    html = load_index_html(missing_index)

    assert "Business Bridge" in html


def test_workspace_layout_helpers_and_missing_document(tmp_path: Path, monkeypatch) -> None:
    company_root = tmp_path / "company" / "Business_Bridge"
    originals_dir = company_root / "originales"
    actualizados_dir = company_root / "actualizados"
    profile_file = company_root / "data.json"

    monkeypatch.setattr("business_bridge.core.workspace.COMPANY_ROOT", company_root)
    monkeypatch.setattr("business_bridge.core.workspace.ORIGINALS_DIR", originals_dir)
    monkeypatch.setattr("business_bridge.core.workspace.ACTUALIZADOS_DIR", actualizados_dir)
    monkeypatch.setattr("business_bridge.core.workspace.COMPANY_PROFILE_FILE", profile_file)

    ensure_company_layout()
    assert not company_layout_is_ready()
    profile_file.write_text("{}", encoding="utf-8")
    assert company_layout_is_ready()

    document = originals_dir / "doc_1__sample.txt"
    document.write_text("hello", encoding="utf-8")
    assert find_uploaded_file("doc_1") == document

    with pytest.raises(FileNotFoundError):
        find_uploaded_file("missing")


def test_decode_uploaded_json_accepts_valid_payloads_and_rejects_invalid() -> None:
    class DummyUpload:
        def __init__(self, raw_bytes: bytes) -> None:
            self.file = SimpleNamespace(read=lambda: raw_bytes)

    upload_utf8: Any = DummyUpload(b'{"name": "Business Bridge"}')
    upload_latin1: Any = DummyUpload(b'{"name": "ni\xf1o"}')
    upload_empty: Any = DummyUpload(b"")
    upload_invalid: Any = DummyUpload(b"not json")
    upload_array: Any = DummyUpload(b"[1, 2, 3]")

    assert decode_uploaded_json(upload_utf8) == {
        "name": "Business Bridge"
    }
    assert decode_uploaded_json(upload_latin1) == {"name": "ni\u00f1o"}

    with pytest.raises(HTTPException, match="empty"):
        decode_uploaded_json(upload_empty)

    with pytest.raises(HTTPException, match="not valid JSON"):
        decode_uploaded_json(upload_invalid)

    with pytest.raises(HTTPException, match="must be an object"):
        decode_uploaded_json(upload_array)
