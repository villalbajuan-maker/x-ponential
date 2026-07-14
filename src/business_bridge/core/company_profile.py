from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

DEFAULT_COMPANY_PROFILE: Dict[str, str] = {
    "business_name": "",
    "nit": "",
    "legal_representative": "",
    "legal_representative_id": "",
    "address": "",
    "city": "",
    "phone": "",
    "email": "",
    "bank_name": "",
    "bank_account_type": "",
    "bank_account_number": "",
}

COMPANY_PROFILE_FIELDS = set(DEFAULT_COMPANY_PROFILE.keys())


def default_company_profile() -> Dict[str, str]:
    """Return a fresh empty company profile."""
    return dict(DEFAULT_COMPANY_PROFILE)


def normalize_company_profile(raw_profile: Dict[str, Any]) -> Dict[str, str]:
    """Normalize a raw profile payload into the canonical string schema."""
    normalized = default_company_profile()
    source_profile: Dict[str, Any] = raw_profile
    if isinstance(raw_profile.get("company_profile"), dict):
        source_profile = raw_profile["company_profile"]
    for field_name in normalized:
        value = source_profile.get(field_name, raw_profile.get(field_name, normalized[field_name]))
        normalized[field_name] = "" if value is None else str(value)
    return normalized


def ensure_company_profile_file(profile_file: Path) -> None:
    """Create the JSON profile file with defaults if it does not exist yet."""
    profile_file.parent.mkdir(parents=True, exist_ok=True)
    if profile_file.exists():
        return
    profile_file.write_text(
        json.dumps(default_company_profile(), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def load_company_profile_raw(profile_file: Path) -> Dict[str, Any]:
    """Load the raw JSON payload from disk without assuming a strict schema."""
    ensure_company_profile_file(profile_file)
    try:
        raw_profile = json.loads(profile_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        raw_profile = {}
    if not isinstance(raw_profile, dict):
        raw_profile = {}
    return raw_profile


def load_company_profile(profile_file: Path) -> Dict[str, str]:
    """Return the normalized company profile used by the API."""
    return normalize_company_profile(load_company_profile_raw(profile_file))


def save_company_profile(profile_file: Path, profile_data: Dict[str, Any]) -> Dict[str, str]:
    """Merge new profile data into the persisted file and return the normalized result."""
    existing_profile = load_company_profile_raw(profile_file)
    normalized_profile = normalize_company_profile(profile_data)
    merged_profile: Dict[str, Any] = dict(existing_profile)
    merged_profile.update(normalized_profile)
    profile_file.write_text(
        json.dumps(merged_profile, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return normalize_company_profile(merged_profile)


def import_company_profile_payload(
    profile_file: Path,
    payload: Dict[str, Any],
) -> Tuple[Dict[str, Any], List[str]]:
    """Import a JSON payload into the persisted company profile."""
    existing_profile = load_company_profile_raw(profile_file)
    merged_profile: Dict[str, Any] = dict(existing_profile)
    imported_keys: List[str] = []

    if isinstance(payload.get("company_profile"), dict):
        company_payload = payload["company_profile"]
        extra_payload = {key: value for key, value in payload.items() if key != "company_profile"}
        merged_profile.update(extra_payload)
        normalized_profile = normalize_company_profile(company_payload)
        imported_keys.extend([key for key in normalized_profile if normalized_profile[key]])
        merged_profile.update(normalized_profile)
    else:
        normalized_profile = normalize_company_profile(payload)
        imported_keys.extend([key for key in normalized_profile if normalized_profile[key]])
        merged_profile.update(payload)
        merged_profile.update(normalized_profile)

    profile_file.write_text(
        json.dumps(merged_profile, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return merged_profile, imported_keys
