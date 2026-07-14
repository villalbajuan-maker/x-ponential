from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Respuesta del health check del servicio FastAPI."""

    status: str
    app_name: str
    version: str
    checkpoint: str
    company_ready: bool


class CompanyProfile(BaseModel):
    """Perfil canonico de empresa almacenado por Business Bridge."""

    business_name: str = ""
    nit: str = ""
    legal_representative: str = ""
    legal_representative_id: str = ""
    address: str = ""
    city: str = ""
    phone: str = ""
    email: str = ""
    bank_name: str = ""
    bank_account_type: str = ""
    bank_account_number: str = ""


class CompanyProfileEnvelope(BaseModel):
    """Envoltorio estandar devuelto para lecturas y actualizaciones del perfil."""

    status: str
    company_profile: CompanyProfile
    saved_to: str


class CompanyProfileImportEnvelope(BaseModel):
    """Carga util de respuesta para importaciones de perfil desde JSON."""

    status: str
    company_profile: CompanyProfile
    saved_to: str
    source_file_name: str
    imported_keys: List[str]
    warnings: List[str]


class DocumentUploadResponse(BaseModel):
    """Metadatos de respuesta para una carga original almacenada."""

    status: str
    document_id: str
    original_file_name: str
    stored_file_name: str
    file_type: str
    saved_to: str
    size_bytes: int


class DetectedItem(BaseModel):
    """Un campo candidato extraido por OCR o por reglas regex."""

    item_id: str
    field_key: str
    label: str
    value: str
    confidence: float
    source: str
    page: Optional[int] = None
    status: str = "pending_review"
    reusable: bool = False


class DocumentExtractionRecord(BaseModel):
    """Registro persistente de revision para un documento procesado."""

    document_id: str
    file_name: str
    file_type: str
    document_type: str
    confidence: float
    raw_text_preview: str
    detected_items: List[DetectedItem]
    missing_fields: List[str]
    warnings: List[str]
    supplemental_answers: Dict[str, str] = Field(default_factory=dict)


class ReviewItemUpdateRequest(BaseModel):
    """Carga util con la decision del usuario para un item detectado."""

    item_id: str
    status: str
    value: Optional[str] = None
    save_to_company_profile: bool = False


class MissingFieldAnswerRequest(BaseModel):
    """Carga util usada cuando la UI le pide al usuario un valor faltante."""

    field_key: str
    value: str
