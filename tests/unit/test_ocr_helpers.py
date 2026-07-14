from __future__ import annotations

from pathlib import Path

from business_bridge.adapters.ocr import clean_value, detect_file_type, normalize_text, safe_preview
from business_bridge.adapters.ocr_text import read_text_file


def test_normalize_text_collapses_spacing_and_hyphenated_line_breaks() -> None:
    text = "  Hola   mundo  \r\nlinea-\ncontinua\n\n  tercera   parte  "

    assert normalize_text(text) == "Hola mundo\nlineacontinua\n\ntercera parte"


def test_clean_value_strips_outer_noise() -> None:
    assert clean_value("  COP $12.345.678 ; ") == "COP $12.345.678"


def test_detect_file_type_uses_extension_or_unknown() -> None:
    assert detect_file_type("anexo.PDF") == "pdf"
    assert detect_file_type("archivo") == "unknown"


def test_safe_preview_truncates_long_text() -> None:
    assert safe_preview("1234567890", limit=4) == "1234..."


def test_read_text_file_falls_back_to_latin1(tmp_path: Path) -> None:
    path = tmp_path / "latin1.txt"
    path.write_bytes(b"ni\xf1o")

    assert read_text_file(path) == "niño"
