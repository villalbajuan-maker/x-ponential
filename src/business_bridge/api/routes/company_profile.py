from __future__ import annotations

from fastapi import APIRouter, File, UploadFile

from business_bridge.api.runtime import prepare_workspace
from business_bridge.api.schemas import (
    CompanyProfile,
    CompanyProfileEnvelope,
    CompanyProfileImportEnvelope,
)
from business_bridge.core import workspace
from business_bridge.services.company_profile_service import (
    get_company_profile as service_get_company_profile,
    import_company_profile as service_import_company_profile,
    update_company_profile as service_update_company_profile,
)


router = APIRouter()


@router.get("/company-profile", response_model=CompanyProfileEnvelope)
def get_company_profile() -> CompanyProfileEnvelope:
    """Devolver el perfil de empresa guardado actualmente."""

    return service_get_company_profile(workspace.COMPANY_PROFILE_FILE)


@router.post("/company-profile/update", response_model=CompanyProfileEnvelope)
def update_company_profile(payload: CompanyProfile) -> CompanyProfileEnvelope:
    """Fusionar el perfil entrante con el perfil persistido."""

    prepare_workspace()
    return service_update_company_profile(payload, workspace.COMPANY_PROFILE_FILE)


@router.post("/company-profile/import", response_model=CompanyProfileImportEnvelope)
async def import_company_profile(file: UploadFile = File(...)) -> CompanyProfileImportEnvelope:
    """Importar un JSON de perfil al almacenamiento canonico de empresa."""

    prepare_workspace()
    return service_import_company_profile(file, workspace.COMPANY_PROFILE_FILE)
