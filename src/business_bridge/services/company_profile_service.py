from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from fastapi import HTTPException, UploadFile

from business_bridge.api.schemas import (
    CompanyProfile,
    CompanyProfileEnvelope,
    CompanyProfileImportEnvelope,
)
from business_bridge.core.audit import audit_event
from business_bridge.core.company_profile import (
    ensure_company_profile_file,
    import_company_profile_payload,
    load_company_profile,
    save_company_profile,
)
from business_bridge.core.workspace import (
    COMPANY_PROFILE_FILE,
    decode_uploaded_json,
    ensure_company_layout,
)


def company_profile_envelope(
    profile_data: Dict[str, Any], profile_file: Path = COMPANY_PROFILE_FILE
) -> CompanyProfileEnvelope:
    """Empaquetar el perfil en el envoltorio de respuesta de la API."""

    return CompanyProfileEnvelope(
        status="ok",
        company_profile=CompanyProfile.model_validate(profile_data),
        saved_to=str(profile_file),
    )


def get_company_profile(profile_file: Path = COMPANY_PROFILE_FILE) -> CompanyProfileEnvelope:
    """Devolver el perfil de empresa guardado actualmente."""

    return company_profile_envelope(load_company_profile(profile_file), profile_file)


def update_company_profile(
    payload: CompanyProfile, profile_file: Path = COMPANY_PROFILE_FILE
) -> CompanyProfileEnvelope:
    """Fusionar los valores entrantes del perfil con el perfil persistido."""

    current_profile = load_company_profile(profile_file)
    incoming_data = payload.model_dump(exclude_unset=True)
    merged_profile = {**current_profile, **incoming_data}
    saved_profile = save_company_profile(profile_file, merged_profile)
    audit_event(
        "company_profile.updated",
        str(profile_file),
        changed_keys=sorted(incoming_data.keys()),
    )
    return company_profile_envelope(saved_profile, profile_file)


def import_company_profile(
    file: UploadFile, profile_file: Path = COMPANY_PROFILE_FILE
) -> CompanyProfileImportEnvelope:
    """Importar un JSON de perfil al almacenamiento canonico de empresa."""

    ensure_company_layout()
    ensure_company_profile_file(profile_file)

    if not file.filename:
        raise HTTPException(status_code=400, detail="Se requiere un nombre de archivo JSON valido.")
    if Path(file.filename).suffix.lower() != ".json":
        raise HTTPException(
            status_code=400,
            detail="Solo se pueden importar archivos JSON como perfiles de empresa.",
        )

    payload = decode_uploaded_json(file)
    merged_profile, imported_keys = import_company_profile_payload(profile_file, payload)
    audit_event(
        "company_profile.imported",
        str(profile_file),
        source_file=file.filename,
        imported_keys=imported_keys,
    )

    return CompanyProfileImportEnvelope(
        status="ok",
        company_profile=CompanyProfile.model_validate(merged_profile),
        saved_to=str(profile_file),
        source_file_name=Path(file.filename).name,
        imported_keys=imported_keys,
        warnings=[],
    )
