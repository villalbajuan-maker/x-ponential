from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from business_bridge.adapters.secop_constants import SECOP_DOWNLOAD_HOSTS
from business_bridge.adapters.secop_utils import (
    _casefold_dict_lookup,
    _collect_query_params,
    _extract_url,
    _format_epoch,
    _first_non_empty,
    _is_allowed_download_url,
    _is_url,
    _json_safe,
    _normalize_text,
    _query_param_case_insensitive,
    _tokenize_search_terms,
    _unique_preserve_order,
    _utc_now_iso,
    escape_soql,
)


@dataclass
class NestedPayload:
    path: Path
    created_at: datetime
    payload: dict[str, object]


def test_escape_soql_doubles_quotes() -> None:
    assert escape_soql("O'Brien") == "O''Brien"


def test_utc_now_iso_is_parseable() -> None:
    value = _utc_now_iso()

    assert datetime.fromisoformat(value)


def test_format_epoch_and_first_non_empty() -> None:
    expected = datetime.fromtimestamp(1_700_000_000, tz=timezone.utc).astimezone().isoformat(
        timespec="seconds"
    )

    assert _format_epoch(1_700_000_000) == expected
    assert _format_epoch("1700000000") == expected
    assert _format_epoch(0) == ""
    assert _first_non_empty(None, "  ", "  hola  ", 7) == "hola"


def test_extract_url_and_casefold_lookup() -> None:
    payload = {"url": "https://example.com", "href": "https://fallback.example"}

    assert _extract_url(payload) == "https://example.com"
    assert _extract_url("https://direct.example") == "https://direct.example"
    assert _casefold_dict_lookup({"Foo": 1}, "foo") == 1


def test_text_normalization_and_tokenization() -> None:
    assert _normalize_text("  hola   mundo \n\n  mundo  ") == "hola mundo mundo"
    assert _tokenize_search_terms("SECOP CO1 NTC 2026 2026") == ["secop", "co1", "ntc", "2026"]
    assert _tokenize_search_terms("abc 123 1234") == ["1234"]


def test_collect_and_filter_query_params() -> None:
    params = _collect_query_params("noticeUID=CO1.NTC.123&noticeUID=CO1.NTC.456&id=7")

    assert params == {"noticeUID": ["CO1.NTC.123", "CO1.NTC.456"], "id": ["7"]}
    assert _query_param_case_insensitive(params, "noticeuid", "id") == [
        "CO1.NTC.123",
        "CO1.NTC.456",
        "7",
    ]
    assert _unique_preserve_order([" a ", "a", "", "b", "b", "c"]) == ["a", "b", "c"]


def test_download_url_validation_accepts_official_hosts() -> None:
    allowed_host = SECOP_DOWNLOAD_HOSTS[0]

    assert _is_url("https://example.com/path")
    assert _is_allowed_download_url(f"https://{allowed_host}/file.pdf")
    assert not _is_allowed_download_url("https://malicious.example/file.pdf")


def test_json_safe_serializes_dataclasses_paths_and_datetimes() -> None:
    payload = NestedPayload(
        path=Path("company/Business_Bridge/data.json"),
        created_at=datetime(2026, 7, 12, 12, 0, tzinfo=timezone.utc),
        payload={"inner_path": Path("/tmp/example")},
    )

    serialized = _json_safe(payload)

    assert serialized["path"] == str(Path("company/Business_Bridge/data.json"))
    assert serialized["created_at"] == "2026-07-12T12:00:00+00:00"
    assert serialized["payload"]["inner_path"] == str(Path("/tmp/example"))
