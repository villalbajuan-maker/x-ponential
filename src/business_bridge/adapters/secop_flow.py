from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from business_bridge.adapters.secop_client import SocrataClient
from business_bridge.adapters.secop_constants import (
    DATASETS,
    DEFAULT_LIMIT,
    SODA_METADATA_URL,
    SECOP_I_DOCUMENT_FIELDS,
    SECOP_I_PROCESS_FIELDS,
    SECOP_II_DOCUMENT_FIELDS,
    SECOP_II_PROCESS_FIELDS,
)
from business_bridge.adapters.secop_models import DatasetMetadataInfo, DocumentInfo, InspectionResult, ParsedSecopInput
from business_bridge.adapters.secop_parsing import parse_secop_input
from business_bridge.adapters.secop_utils import (
    _extract_url,
    _first_non_empty,
    _query_param_case_insensitive,
    _unique_preserve_order,
    _utc_now_iso,
)
from business_bridge.core.audit import log_event


def _candidate_dataset_families(platform: str) -> Dict[str, List[str]]:
    """Devolver las familias de conjuntos de datos que se deben consultar para una plataforma."""

    if platform == "secop_ii":
        return {
            "process": [
                DATASETS["secop_ii_procesos"],
                DATASETS["secop_i_procesos_desde_2018"],
                DATASETS["secop_i_procesos_hasta_2017"],
            ],
            "documents": [
                DATASETS["secop_ii_archivos_2022"],
                DATASETS["secop_ii_archivos_2023"],
                DATASETS["secop_ii_archivos_2024"],
                DATASETS["secop_ii_archivos_desde_2025"],
                DATASETS["secop_i_archivos_desde_2019"],
                DATASETS["secop_i_archivos_hasta_2018"],
            ],
        }
    if platform == "secop_i":
        return {
            "process": [
                DATASETS["secop_i_procesos_desde_2018"],
                DATASETS["secop_i_procesos_hasta_2017"],
                DATASETS["secop_ii_procesos"],
            ],
            "documents": [
                DATASETS["secop_i_archivos_desde_2019"],
                DATASETS["secop_i_archivos_hasta_2018"],
                DATASETS["secop_ii_archivos_2022"],
                DATASETS["secop_ii_archivos_2023"],
                DATASETS["secop_ii_archivos_2024"],
                DATASETS["secop_ii_archivos_desde_2025"],
            ],
        }
    return {
        "process": [
            DATASETS["secop_ii_procesos"],
            DATASETS["secop_i_procesos_desde_2018"],
            DATASETS["secop_i_procesos_hasta_2017"],
        ],
        "documents": [
            DATASETS["secop_ii_archivos_2022"],
            DATASETS["secop_ii_archivos_2023"],
            DATASETS["secop_ii_archivos_2024"],
            DATASETS["secop_ii_archivos_desde_2025"],
            DATASETS["secop_i_archivos_desde_2019"],
            DATASETS["secop_i_archivos_hasta_2018"],
        ],
    }


def _dataset_family_label(dataset_id: str) -> str:
    """Etiquetar un id de conjunto de datos como SECOP I o SECOP II."""

    secop_ii_ids = {
        DATASETS["secop_ii_procesos"],
        DATASETS["secop_ii_archivos_2022"],
        DATASETS["secop_ii_archivos_2023"],
        DATASETS["secop_ii_archivos_2024"],
        DATASETS["secop_ii_archivos_desde_2025"],
    }
    return "SECOP II" if dataset_id in secop_ii_ids else "SECOP I"


def _normalize_process_row(row: Mapping[str, Any]) -> Dict[str, Any]:
    """Aplanar campos URL anidados en filas de proceso para mostrarlos mejor."""

    normalized = dict(row)
    if isinstance(normalized.get("urlproceso"), dict):
        normalized["urlproceso"] = normalized["urlproceso"].get("url", "")
    if isinstance(normalized.get("ruta_proceso_en_secop_i"), dict):
        normalized["ruta_proceso_en_secop_i"] = normalized["ruta_proceso_en_secop_i"].get("url", "")
    return normalized


def _process_row_key(row: Mapping[str, Any]) -> Tuple[str, str, str, str, str, str]:
    """Construir una llave de deduplicacion para filas de proceso."""

    return (
        _first_non_empty(row.get("dataset_id")),
        _first_non_empty(row.get("id_del_proceso")),
        _first_non_empty(row.get("referencia_del_proceso")),
        _first_non_empty(row.get("numero_de_constancia")),
        _first_non_empty(row.get("numero_de_proceso")),
        _first_non_empty(row.get("uid")),
    )


def _process_summary_from_row(
    dataset_id: str, row: Mapping[str, Any], dataset_name: str
) -> Dict[str, Any]:
    """Convertir una fila de proceso en el resumen compacto que ve la UI."""

    if dataset_id == DATASETS["secop_ii_procesos"]:
        return {
            "dataset_id": dataset_id,
            "dataset_name": dataset_name,
            "process_id": _first_non_empty(row.get("id_del_proceso")),
            "reference": _first_non_empty(row.get("referencia_del_proceso")),
            "entity": _first_non_empty(row.get("entidad")),
            "title": _first_non_empty(row.get("nombre_del_procedimiento")),
            "status": _first_non_empty(row.get("estado_del_procedimiento"), row.get("fase")),
            "amount": _first_non_empty(row.get("precio_base")),
            "document_url": _extract_url(row.get("urlproceso")),
        }

    return {
        "dataset_id": dataset_id,
        "dataset_name": dataset_name,
        "process_id": _first_non_empty(row.get("numero_de_constancia")),
        "reference": _first_non_empty(row.get("numero_de_proceso"), row.get("uid")),
        "entity": _first_non_empty(row.get("nombre_entidad")),
        "title": _first_non_empty(
            row.get("objeto_a_contratar"), row.get("detalle_del_objeto_a_contratar")
        ),
        "status": _first_non_empty(row.get("estado_del_proceso")),
        "amount": _first_non_empty(row.get("cuantia_proceso")),
        "document_url": _extract_url(row.get("ruta_proceso_en_secop_i")),
    }


def _document_from_row(
    dataset_id: str, row: Mapping[str, Any], dataset_name: str, dataset_source_url: str
) -> DocumentInfo:
    """Convertir una fila de documento en el modelo normalizado de documento."""

    if dataset_id in {
        DATASETS["secop_ii_archivos_2022"],
        DATASETS["secop_ii_archivos_2023"],
        DATASETS["secop_ii_archivos_2024"],
        DATASETS["secop_ii_archivos_desde_2025"],
    }:
        download_url = _extract_url(row.get("url_descarga_documento"))
        official_url = download_url
        return DocumentInfo(
            dataset_id=dataset_id,
            dataset_name=dataset_name,
            source_family=_dataset_family_label(dataset_id),
            dataset_source_url=dataset_source_url,
            process_identifier=_first_non_empty(row.get("proceso")),
            document_identifier=_first_non_empty(row.get("id_documento")),
            title=_first_non_empty(row.get("nombre_archivo"), row.get("descripci_n")),
            file_name=_first_non_empty(row.get("nombre_archivo")),
            extension=_first_non_empty(row.get("extensi_n")),
            description=_first_non_empty(row.get("descripci_n")),
            entity=_first_non_empty(row.get("entidad")),
            contract_number=_first_non_empty(row.get("n_mero_de_contrato")),
            download_url=download_url,
            official_url=official_url,
            source_field="proceso|n_mero_de_contrato",
            raw_row=dict(row),
        )

    download_url = _extract_url(row.get("ruta_descarga"))
    return DocumentInfo(
        dataset_id=dataset_id,
        dataset_name=dataset_name,
        source_family=_dataset_family_label(dataset_id),
        dataset_source_url=dataset_source_url,
        process_identifier=_first_non_empty(row.get("numero_de_constancia")),
        document_identifier=_first_non_empty(row.get("identificador")),
        title=_first_non_empty(row.get("titulo"), row.get("nombrearchivo")),
        file_name=_first_non_empty(row.get("nombrearchivo")),
        extension=_first_non_empty(row.get("extension")),
        description=_first_non_empty(row.get("descripcion")),
        entity="",
        contract_number=_first_non_empty(row.get("numero_de_constancia")),
        download_url=download_url,
        official_url=download_url,
        source_field="numero_de_constancia",
        raw_row=dict(row),
    )


def _group_documents(documents: Sequence[DocumentInfo]) -> List[Dict[str, Any]]:
    """Agrupar documentos primero por familia de origen y luego por conjunto de datos."""

    grouped: List[Dict[str, Any]] = []
    source_index: Dict[str, Dict[str, Any]] = {}

    for doc in documents:
        source_key = doc.source_family or "Sin fuente"
        source_group = source_index.get(source_key)
        if source_group is None:
            source_group = {
                "source_family": source_key,
                "document_count": 0,
                "datasets": [],
            }
            source_group["_dataset_index"] = {}
            source_index[source_key] = source_group
            grouped.append(source_group)

        source_group["document_count"] += 1
        dataset_key = (doc.dataset_id, doc.dataset_name, doc.dataset_source_url)
        dataset_index: Dict[Tuple[str, str, str], Dict[str, Any]] = source_group["_dataset_index"]
        dataset_group = dataset_index.get(dataset_key)
        if dataset_group is None:
            dataset_group = {
                "dataset_id": doc.dataset_id,
                "dataset_name": doc.dataset_name,
                "dataset_source_url": doc.dataset_source_url,
                "document_count": 0,
                "documents": [],
            }
            dataset_index[dataset_key] = dataset_group
            source_group["datasets"].append(dataset_group)

        dataset_group["document_count"] += 1
        dataset_group["documents"].append(doc)

    for source_group in grouped:
        source_group.pop("_dataset_index", None)
        source_group["dataset_count"] = len(source_group["datasets"])
        for dataset_group in source_group["datasets"]:
            dataset_group["documents"] = [doc.to_dict() for doc in dataset_group["documents"]]

    return grouped


def _collect_metadata(
    client: SocrataClient, dataset_ids: Sequence[str]
) -> List[DatasetMetadataInfo]:
    """Traer metadatos de varios conjuntos de datos en paralelo y preservar el orden pedido."""

    ordered_ids = _unique_preserve_order(dataset_ids)
    metadata: List[DatasetMetadataInfo] = []
    if not ordered_ids:
        return metadata
    with ThreadPoolExecutor(max_workers=min(8, len(ordered_ids))) as executor:
        futures = {
            executor.submit(client.get_metadata, dataset_id): dataset_id
            for dataset_id in ordered_ids
        }
        for future in as_completed(futures):
            try:
                metadata.append(future.result())
            except Exception as exc:
                dataset_id = futures[future]
                log_event(
                    logging.WARNING,
                    "secop.metadata_fetch_failed",
                    dataset_id,
                    error_type=exc.__class__.__name__,
                    error_message=str(exc),
                )
                metadata.append(
                    DatasetMetadataInfo(
                        dataset_id=dataset_id,
                        dataset_name=dataset_id,
                        queried_at=_utc_now_iso(),
                        last_update="no disponible",
                        last_update_source="no disponible",
                        source_url=SODA_METADATA_URL.format(dataset_id=dataset_id),
                    )
                )
    metadata.sort(
        key=lambda item: (
            ordered_ids.index(item.dataset_id) if item.dataset_id in ordered_ids else 999
        )
    )
    return metadata


def _metadata_by_dataset_id(
    metadata: Sequence[DatasetMetadataInfo],
) -> Dict[str, DatasetMetadataInfo]:
    """Indexar los metadatos por id de conjunto de datos para consultas rapidas."""

    return {item.dataset_id: item for item in metadata}


def _build_candidates(parsed: ParsedSecopInput) -> List[str]:
    """Armar los candidatos de identificador que se deben buscar por coincidencia exacta."""

    candidates = list(parsed.identifier_candidates or (parsed.identifier,))
    if parsed.query_params:
        candidates.extend(
            _query_param_case_insensitive(
                parsed.query_params, "noticeUID", "processUID", "processId", "id"
            )
        )
        candidates.extend(
            _query_param_case_insensitive(
                parsed.query_params,
                "numConstancia",
                "numeroConstancia",
                "idProceso",
                "IDProceso",
            )
        )
    if (
        parsed.platform == "secop_ii"
        and parsed.identifier
        and parsed.identifier.upper().startswith("CO1.")
    ):
        candidates.append(parsed.identifier)
    if parsed.platform == "secop_i" and parsed.identifier:
        candidates.append(parsed.identifier)
    return _unique_preserve_order(candidates)


def _search_process_rows(
    client: SocrataClient,
    parsed: ParsedSecopInput,
    dataset_ids: Sequence[str],
) -> List[Dict[str, Any]]:
    """Encontrar filas de proceso en los conjuntos de datos candidatos usando coincidencias exactas."""

    candidates = _build_candidates(parsed)
    results: List[Dict[str, Any]] = []
    for dataset_id in _unique_preserve_order(dataset_ids):
        if dataset_id == DATASETS["secop_ii_procesos"]:
            rows = client.query_exact_any(dataset_id, SECOP_II_PROCESS_FIELDS, candidates, limit=20)
        else:
            rows = client.query_exact_any(dataset_id, SECOP_I_PROCESS_FIELDS, candidates, limit=20)
        for row in rows:
            normalized = _normalize_process_row(row)
            normalized["dataset_id"] = dataset_id
            normalized["source_family"] = _dataset_family_label(dataset_id)
            if normalized not in results:
                results.append(normalized)

    return results


def _derive_document_candidates(
    parsed: ParsedSecopInput, process_rows: Sequence[Dict[str, Any]]
) -> List[str]:
    """Derivar terminos de busqueda de documentos desde la entrada y las filas de proceso."""

    candidates = list(_build_candidates(parsed))
    for row in process_rows:
        candidates.extend(
            _unique_preserve_order(
                [
                    _first_non_empty(row.get("id_del_proceso")),
                    _first_non_empty(row.get("id_del_portafolio")),
                    _first_non_empty(row.get("referencia_del_proceso")),
                    _first_non_empty(row.get("numero_de_constancia")),
                    _first_non_empty(row.get("numero_de_proceso")),
                    _first_non_empty(row.get("uid")),
                ]
            )
        )
    return _unique_preserve_order(candidates)


def _search_documents(
    client: SocrataClient,
    parsed: ParsedSecopInput,
    process_rows: Sequence[Dict[str, Any]],
    dataset_ids: Sequence[str],
) -> List[DocumentInfo]:
    """Encontrar filas de documentos en los conjuntos de datos candidatos usando coincidencias exactas."""

    candidates = _derive_document_candidates(parsed, process_rows)
    docs: List[DocumentInfo] = []
    for dataset_id in _unique_preserve_order(dataset_ids):
        if dataset_id in {
            DATASETS["secop_ii_archivos_2022"],
            DATASETS["secop_ii_archivos_2023"],
            DATASETS["secop_ii_archivos_2024"],
            DATASETS["secop_ii_archivos_desde_2025"],
        }:
            rows = client.query_exact_any(
                dataset_id, SECOP_II_DOCUMENT_FIELDS, candidates, limit=20
            )
        else:
            rows = client.query_exact_any(dataset_id, SECOP_I_DOCUMENT_FIELDS, candidates, limit=20)
        metadata = client.get_metadata(dataset_id)
        dataset_name = metadata.dataset_name
        dataset_source_url = metadata.source_url
        for row in rows:
            docs.append(_document_from_row(dataset_id, row, dataset_name, dataset_source_url))

    unique_docs: List[DocumentInfo] = []
    seen_keys = set()
    for doc in docs:
        key = (doc.dataset_id, doc.document_identifier, doc.download_url, doc.file_name)
        if key in seen_keys:
            continue
        seen_keys.add(key)
        unique_docs.append(doc)
    return unique_docs


def inspect_secop_value(
    client: SocrataClient, value: str, *, metadata_limit: int = DEFAULT_LIMIT
) -> InspectionResult:
    """Ejecutar el flujo completo de inspeccion SECOP para un valor de entrada."""

    parsed = parse_secop_input(value)
    families = _candidate_dataset_families(parsed.platform)
    metadata_dataset_ids = families["process"] + families["documents"]
    metadata = _collect_metadata(client, metadata_dataset_ids)
    process_rows = _search_process_rows(client, parsed, families["process"])
    documents = _search_documents(client, parsed, process_rows, families["documents"])

    document_groups = _group_documents(documents)

    notes: List[str] = []
    if not process_rows:
        notes.append("No se encontrÃƒÂ³ coincidencia exacta en los datasets de procesos consultados.")
    if not documents:
        notes.append(
            "No se encontraron documentos exactos en los datasets de archivos consultados."
        )
    if parsed.platform == "unknown":
        notes.append(
            "El input no revelÃƒÂ³ una plataforma con certeza; se consultaron ambas familias de datasets."
        )
    if parsed.input_kind == "empty":
        notes.append("El valor de entrada estÃƒÂ¡ vacÃƒÂ­o.")

    return InspectionResult(
        queried_at=_utc_now_iso(),
        parsed_input=parsed,
        metadata=metadata,
        process_rows=process_rows,
        documents=documents,
        document_groups=document_groups,
        notes=notes,
    )
