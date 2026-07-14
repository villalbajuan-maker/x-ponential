from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple

from business_bridge.adapters.secop_utils import _json_safe


@dataclass(frozen=True)
class ParsedSecopInput:
    """Representacion normalizada de la consulta SECOP del usuario."""

    raw_value: str
    input_kind: str
    platform: str
    identifier: str
    original_url: str = ""
    domain: str = ""
    path: str = ""
    query_params: Dict[str, List[str]] = field(default_factory=dict)
    matched_parameters: Tuple[str, ...] = ()
    identifier_candidates: Tuple[str, ...] = ()

    def to_dict(self) -> Dict[str, Any]:
        """Serializar la entrada parseada a primitivas seguras para JSON."""

        return _json_safe(self)


@dataclass
class DatasetMetadataInfo:
    """Instantanea de metadatos para un conjunto de datos de Socrata."""

    dataset_id: str
    dataset_name: str
    queried_at: str
    last_update: str
    last_update_source: str
    publication_date: str = ""
    rows_updated_at: str = ""
    view_last_modified: str = ""
    created_at: str = ""
    columns: List[str] = field(default_factory=list)
    source_url: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Serializar los metadatos del dataset a primitivas seguras para JSON."""

        return _json_safe(self)


@dataclass
class DocumentInfo:
    """Registro normalizado de documento usado por la UI y la API del inspector."""

    dataset_id: str
    dataset_name: str
    source_family: str
    dataset_source_url: str
    process_identifier: str
    document_identifier: str
    title: str
    file_name: str
    extension: str
    description: str
    entity: str = ""
    contract_number: str = ""
    download_url: str = ""
    official_url: str = ""
    source_field: str = ""
    raw_row: Dict[str, Any] = field(default_factory=dict, repr=False)

    def to_dict(self) -> Dict[str, Any]:
        """Serializar el registro del documento a primitivas seguras para JSON."""

        return _json_safe(self)


@dataclass
class InspectionResult:
    """Respuesta completa devuelta por una ejecucion de inspeccion."""

    queried_at: str
    parsed_input: ParsedSecopInput
    metadata: List[DatasetMetadataInfo]
    process_rows: List[Dict[str, Any]]
    documents: List[DocumentInfo]
    document_groups: List[Dict[str, Any]] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Serializar el resultado de inspeccion a primitivas seguras para JSON."""

        return _json_safe(self)
