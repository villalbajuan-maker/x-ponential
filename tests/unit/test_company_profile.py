from __future__ import annotations

import json
from pathlib import Path

from business_bridge.core.company_profile import (
    COMPANY_PROFILE_FIELDS,
    default_company_profile,
    ensure_company_profile_file,
    import_company_profile_payload,
    load_company_profile,
    load_company_profile_raw,
    normalize_company_profile,
    save_company_profile,
)


FIXTURES_DIR = Path(__file__).resolve().parents[1] / "fixtures"
PROFILE_IMPORT_FIXTURE_PATH = FIXTURES_DIR / "company_profile" / "import_payload.json"


def test_default_company_profile_has_expected_shape() -> None:
    profile = default_company_profile()

    assert set(profile.keys()) == COMPANY_PROFILE_FIELDS
    assert all(value == "" for value in profile.values())


def test_normalize_company_profile_supports_nested_payload() -> None:
    profile = normalize_company_profile(
        {
            "company_profile": {
                "business_name": "Business Bridge SAS",
                "nit": 123456789,
                "email": None,
            }
        }
    )

    assert profile["business_name"] == "Business Bridge SAS"
    assert profile["nit"] == "123456789"
    assert profile["email"] == ""


def test_save_and_load_company_profile_roundtrip(tmp_path: Path) -> None:
    profile_file = tmp_path / "data.json"

    saved_profile = save_company_profile(
        profile_file,
        {
            "business_name": "Business Bridge SAS",
            "city": "Bogota",
        },
    )

    assert profile_file.exists()
    assert saved_profile["business_name"] == "Business Bridge SAS"
    assert load_company_profile(profile_file)["city"] == "Bogota"
    assert load_company_profile_raw(profile_file)["business_name"] == "Business Bridge SAS"


def test_import_company_profile_payload_preserves_extras(tmp_path: Path) -> None:
    profile_file = tmp_path / "data.json"
    ensure_company_profile_file(profile_file)
    payload = json.loads(PROFILE_IMPORT_FIXTURE_PATH.read_text(encoding="utf-8"))

    merged_profile, imported_keys = import_company_profile_payload(
        profile_file,
        payload,
    )

    assert merged_profile["workflow"] == "pilot"
    assert merged_profile["business_name"] == "Business Bridge SAS"
    assert merged_profile["email"] == "hello@businessbridge.co"
    assert merged_profile["nit"] == "901234567-8"
    assert "business_name" in imported_keys
    assert "email" in imported_keys
    assert "nit" in imported_keys


def test_load_company_profile_raw_handles_invalid_json(tmp_path: Path) -> None:
    profile_file = tmp_path / "data.json"
    profile_file.write_text("not json", encoding="utf-8")

    assert load_company_profile_raw(profile_file) == {}


def test_normalize_company_profile_supports_flat_payload() -> None:
    profile = normalize_company_profile(
        {
            "business_name": "Business Bridge SAS",
            "nit": 123456789,
            "city": "Bogota",
        }
    )

    assert profile["business_name"] == "Business Bridge SAS"
    assert profile["nit"] == "123456789"
    assert profile["city"] == "Bogota"
    assert profile["email"] == ""


def test_ensure_company_profile_file_is_idempotent(tmp_path: Path) -> None:
    profile_file = tmp_path / "company" / "data.json"

    ensure_company_profile_file(profile_file)
    profile_file.write_text('{"business_name": "Already here"}\n', encoding="utf-8")
    ensure_company_profile_file(profile_file)

    assert profile_file.read_text(encoding="utf-8") == '{"business_name": "Already here"}\n'
