from __future__ import annotations

from business_bridge.adapters.secop import parse_secop_input


def test_parse_secop_input_detects_secop_ii_identifier() -> None:
    parsed = parse_secop_input("CO1.NTC.1234567")

    assert parsed.platform == "secop_ii"
    assert parsed.input_kind == "identifier"
    assert parsed.identifier == "CO1.NTC.1234567"
    assert "secop-ii-id" in parsed.matched_parameters


def test_parse_secop_input_detects_secop_i_constancia() -> None:
    parsed = parse_secop_input("12-34-567890")

    assert parsed.platform == "secop_i"
    assert parsed.input_kind == "constancia"
    assert parsed.identifier == "12-34-567890"
    assert "constancia" in parsed.matched_parameters


def test_parse_secop_input_detects_secop_ii_url() -> None:
    parsed = parse_secop_input(
        "https://community.secop.gov.co/Process/NoticeDetail?noticeUID=CO1.NTC.1234567"
    )

    assert parsed.platform == "secop_ii"
    assert parsed.input_kind == "url"
    assert parsed.original_url.startswith("https://community.secop.gov.co/")
    assert parsed.identifier == "CO1.NTC.1234567"


def test_parse_secop_input_handles_secop_i_url_and_generic_reference() -> None:
    secop_i = parse_secop_input(
        "https://www.contratos.gov.co/consultas/detalleProceso.do?numConstancia=12-34-567890"
    )
    generic = parse_secop_input("LP-2026-001")

    assert secop_i.platform == "secop_i"
    assert secop_i.input_kind == "url"
    assert secop_i.identifier == "12-34-567890"
    assert "numConstancia" in secop_i.matched_parameters
    assert generic.platform == "unknown"
    assert generic.input_kind == "reference"
    assert "generic-reference" in generic.matched_parameters
