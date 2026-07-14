from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from business_bridge.adapters.secop_constants import DATASETS
from business_bridge.adapters.secop_flow import (
    _build_candidates,
    _candidate_dataset_families,
    _collect_metadata,
    _dataset_family_label,
    _derive_document_candidates,
    _document_from_row,
    _group_documents,
    _metadata_by_dataset_id,
    _normalize_process_row,
    _process_row_key,
    _process_summary_from_row,
    _search_documents,
    _search_process_rows,
    inspect_secop_value,
)
from business_bridge.adapters.secop_models import (
    DatasetMetadataInfo,
    DocumentInfo,
    ParsedSecopInput,
)
from business_bridge.adapters.secop_parsing import parse_secop_input


def _metadata(dataset_id: str, dataset_name: str | None = None) -> DatasetMetadataInfo:
    now = datetime(2026, 7, 12, 12, 0, tzinfo=timezone.utc).isoformat()
    return DatasetMetadataInfo(
        dataset_id=dataset_id,
        dataset_name=dataset_name or dataset_id,
        queried_at=now,
        last_update=now,
        last_update_source="rowsUpdatedAt",
        source_url=f"https://example.com/{dataset_id}.json",
    )


class FakeSocrataClient:
    def __init__(
        self,
        *,
        metadata_map: dict[str, DatasetMetadataInfo] | None = None,
        process_rows_by_dataset: dict[str, list[dict[str, Any]]] | None = None,
        document_rows_by_dataset: dict[str, list[dict[str, Any]]] | None = None,
        failing_metadata_ids: set[str] | None = None,
    ) -> None:
        self.metadata_map = metadata_map or {}
        self.process_rows_by_dataset = process_rows_by_dataset or {}
        self.document_rows_by_dataset = document_rows_by_dataset or {}
        self.failing_metadata_ids = failing_metadata_ids or set()
        self.metadata_calls: list[str] = []
        self.query_calls: list[tuple[str, tuple[str, ...], tuple[str, ...], int]] = []

    def get_metadata(self, dataset_id: str) -> DatasetMetadataInfo:
        self.metadata_calls.append(dataset_id)
        if dataset_id in self.failing_metadata_ids:
            raise RuntimeError("metadata boom")
        return self.metadata_map.get(dataset_id, _metadata(dataset_id))

    def query_exact_any(
        self,
        dataset_id: str,
        field_names: tuple[str, ...] | list[str],
        candidate_values: tuple[str, ...] | list[str],
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        self.query_calls.append((dataset_id, tuple(field_names), tuple(candidate_values), limit))
        if dataset_id in self.process_rows_by_dataset:
            return [dict(row) for row in self.process_rows_by_dataset[dataset_id]]
        if dataset_id in self.document_rows_by_dataset:
            return [dict(row) for row in self.document_rows_by_dataset[dataset_id]]
        return []


def test_dataset_helpers_and_row_normalization() -> None:
    families_ii = _candidate_dataset_families("secop_ii")
    families_i = _candidate_dataset_families("secop_i")
    families_unknown = _candidate_dataset_families("unknown")

    assert families_ii["process"][0] == DATASETS["secop_ii_procesos"]
    assert families_i["documents"][0] == DATASETS["secop_i_archivos_desde_2019"]
    assert families_unknown["process"][1] == DATASETS["secop_i_procesos_desde_2018"]
    assert _dataset_family_label(DATASETS["secop_ii_archivos_2024"]) == "SECOP II"
    assert _dataset_family_label(DATASETS["secop_i_archivos_hasta_2018"]) == "SECOP I"

    normalized = _normalize_process_row(
        {
            "urlproceso": {"url": "https://example.com/proceso"},
            "ruta_proceso_en_secop_i": {"url": "https://example.com/proceso-i"},
        }
    )

    assert normalized["urlproceso"] == "https://example.com/proceso"
    assert normalized["ruta_proceso_en_secop_i"] == "https://example.com/proceso-i"
    assert _process_row_key(
        {
            "dataset_id": "abc",
            "id_del_proceso": "1",
            "referencia_del_proceso": "2",
            "numero_de_constancia": "3",
            "numero_de_proceso": "4",
            "uid": "5",
        }
    ) == ("abc", "1", "2", "3", "4", "5")


def test_process_and_document_helpers_cover_both_families() -> None:
    secop_ii_metadata = _metadata(DATASETS["secop_ii_procesos"], "Procesos SECOP II")
    secop_i_metadata = _metadata(DATASETS["secop_i_procesos_desde_2018"], "Procesos SECOP I")

    secop_ii_summary = _process_summary_from_row(
        DATASETS["secop_ii_procesos"],
        {
            "id_del_proceso": "CO1.NTC.1234567",
            "referencia_del_proceso": "REF-2",
            "entidad": "Entidad II",
            "nombre_del_procedimiento": "Obra II",
            "estado_del_procedimiento": "Abierto",
            "precio_base": "1000",
            "urlproceso": {"url": "https://example.com/proceso-ii"},
        },
        secop_ii_metadata.dataset_name,
    )
    secop_i_summary = _process_summary_from_row(
        DATASETS["secop_i_procesos_desde_2018"],
        {
            "numero_de_constancia": "12-34-567890",
            "numero_de_proceso": "LP-2026-001",
            "nombre_entidad": "Entidad I",
            "objeto_a_contratar": "Obra I",
            "estado_del_proceso": "Cerrado",
            "cuantia_proceso": "2000",
            "ruta_proceso_en_secop_i": {"url": "https://example.com/proceso-i"},
        },
        secop_i_metadata.dataset_name,
    )

    secop_ii_doc = _document_from_row(
        DATASETS["secop_ii_archivos_2024"],
        {
            "proceso": "CO1.NTC.1234567",
            "id_documento": "DOC-1",
            "nombre_archivo": "anexo.pdf",
            "extensi_n": "pdf",
            "descripci_n": "Anexo",
            "entidad": "Entidad II",
            "n_mero_de_contrato": "CT-1",
            "url_descarga_documento": {"url": "https://example.com/anexo.pdf"},
        },
        "Archivos SECOP II",
        "https://example.com/secop-ii.json",
    )
    secop_i_doc = _document_from_row(
        DATASETS["secop_i_archivos_desde_2019"],
        {
            "numero_de_constancia": "12-34-567890",
            "identificador": "DOC-2",
            "titulo": "Pliego",
            "nombrearchivo": "pliego.docx",
            "extension": "docx",
            "descripcion": "Pliego",
            "ruta_descarga": {"url": "https://example.com/pliego.docx"},
        },
        "Archivos SECOP I",
        "https://example.com/secop-i.json",
    )

    assert secop_ii_summary["process_id"] == "CO1.NTC.1234567"
    assert secop_ii_summary["document_url"] == "https://example.com/proceso-ii"
    assert secop_i_summary["process_id"] == "12-34-567890"
    assert secop_i_summary["document_url"] == "https://example.com/proceso-i"
    assert secop_ii_doc.source_family == "SECOP II"
    assert secop_ii_doc.download_url == "https://example.com/anexo.pdf"
    assert secop_i_doc.source_family == "SECOP I"
    assert secop_i_doc.download_url == "https://example.com/pliego.docx"


def test_group_documents_and_metadata_index() -> None:
    documents = [
        DocumentInfo(
            dataset_id=DATASETS["secop_ii_archivos_2024"],
            dataset_name="Archivos SECOP II",
            source_family="SECOP II",
            dataset_source_url="https://example.com/secop-ii.json",
            process_identifier="CO1.NTC.1234567",
            document_identifier="DOC-1",
            title="Anexo",
            file_name="anexo.pdf",
            extension="pdf",
            description="Anexo",
            download_url="https://example.com/anexo.pdf",
            official_url="https://example.com/anexo.pdf",
        ),
        DocumentInfo(
            dataset_id=DATASETS["secop_ii_archivos_2024"],
            dataset_name="Archivos SECOP II",
            source_family="SECOP II",
            dataset_source_url="https://example.com/secop-ii.json",
            process_identifier="CO1.NTC.1234567",
            document_identifier="DOC-2",
            title="Pliego",
            file_name="pliego.docx",
            extension="docx",
            description="Pliego",
            download_url="https://example.com/pliego.docx",
            official_url="https://example.com/pliego.docx",
        ),
        DocumentInfo(
            dataset_id=DATASETS["secop_i_archivos_desde_2019"],
            dataset_name="Archivos SECOP I",
            source_family="SECOP I",
            dataset_source_url="https://example.com/secop-i.json",
            process_identifier="12-34-567890",
            document_identifier="DOC-3",
            title="Soporte",
            file_name="soporte.pdf",
            extension="pdf",
            description="Soporte",
            download_url="https://example.com/soporte.pdf",
            official_url="https://example.com/soporte.pdf",
        ),
    ]

    grouped = _group_documents(documents)
    metadata_index = _metadata_by_dataset_id(
        [
            _metadata(DATASETS["secop_ii_archivos_2024"], "Archivos SECOP II"),
            _metadata(DATASETS["secop_i_archivos_desde_2019"], "Archivos SECOP I"),
        ]
    )

    assert grouped[0]["source_family"] == "SECOP II"
    assert grouped[0]["document_count"] == 2
    assert grouped[0]["dataset_count"] == 1
    assert grouped[0]["datasets"][0]["documents"][0]["document_identifier"] == "DOC-1"
    assert metadata_index[DATASETS["secop_ii_archivos_2024"]].dataset_name == "Archivos SECOP II"


def test_collect_metadata_preserves_order_and_falls_back_on_failure(monkeypatch) -> None:
    client: Any = FakeSocrataClient(
        metadata_map={
            DATASETS["secop_ii_procesos"]: _metadata(DATASETS["secop_ii_procesos"], "Procesos II"),
        },
        failing_metadata_ids={DATASETS["secop_i_procesos_desde_2018"]},
    )
    logged_events: list[dict[str, Any]] = []
    monkeypatch.setattr(
        "business_bridge.adapters.secop_flow.log_event",
        lambda *args, **kwargs: logged_events.append({"args": args, "kwargs": kwargs}),
    )

    metadata = _collect_metadata(
        client,
        [
            DATASETS["secop_i_procesos_desde_2018"],
            DATASETS["secop_ii_procesos"],
            DATASETS["secop_i_procesos_desde_2018"],
        ],
    )

    assert [item.dataset_id for item in metadata] == [
        DATASETS["secop_i_procesos_desde_2018"],
        DATASETS["secop_ii_procesos"],
    ]
    assert metadata[0].dataset_name == DATASETS["secop_i_procesos_desde_2018"]
    assert metadata[1].dataset_name == "Procesos II"
    assert logged_events


def test_build_and_search_candidates_cover_helpers() -> None:
    parsed = ParsedSecopInput(
        raw_value="CO1.NTC.1234567",
        input_kind="url",
        platform="secop_ii",
        identifier="CO1.NTC.1234567",
        query_params={
            "noticeUID": ["CO1.NTC.1234567"],
            "id": ["CO1.NTC.1234567"],
        },
        identifier_candidates=("CO1.NTC.1234567", "CO1.NTC.1234567"),
    )
    process_rows = [
        {
            "id_del_proceso": "CO1.NTC.1234567",
            "referencia_del_proceso": "REF-2",
            "numero_de_constancia": "12-34-567890",
            "numero_de_proceso": "LP-2026-001",
            "uid": "UID-1",
        }
    ]

    assert _build_candidates(parsed) == ["CO1.NTC.1234567"]
    assert _derive_document_candidates(parsed, process_rows) == [
        "CO1.NTC.1234567",
        "REF-2",
        "12-34-567890",
        "LP-2026-001",
        "UID-1",
    ]

    client: Any = FakeSocrataClient(
        metadata_map={
            DATASETS["secop_ii_procesos"]: _metadata(DATASETS["secop_ii_procesos"], "Procesos II"),
            DATASETS["secop_ii_archivos_2024"]: _metadata(
                DATASETS["secop_ii_archivos_2024"], "Archivos SECOP II"
            ),
        },
        process_rows_by_dataset={
            DATASETS["secop_ii_procesos"]: [
                {
                    "id_del_proceso": "CO1.NTC.1234567",
                    "referencia_del_proceso": "REF-2",
                    "entidad": "Entidad II",
                    "nombre_del_procedimiento": "Obra II",
                    "estado_del_procedimiento": "Abierto",
                    "precio_base": "1000",
                    "urlproceso": {"url": "https://example.com/proceso-ii"},
                }
            ]
        },
        document_rows_by_dataset={
            DATASETS["secop_ii_archivos_2024"]: [
                {
                    "proceso": "CO1.NTC.1234567",
                    "id_documento": "DOC-1",
                    "nombre_archivo": "anexo.pdf",
                    "extensi_n": "pdf",
                    "descripci_n": "Anexo",
                    "entidad": "Entidad II",
                    "n_mero_de_contrato": "CT-1",
                    "url_descarga_documento": {"url": "https://example.com/anexo.pdf"},
                }
            ]
        },
    )

    process_hits = _search_process_rows(
        client,
        parse_secop_input("CO1.NTC.1234567"),
        [DATASETS["secop_ii_procesos"]],
    )
    document_hits = _search_documents(
        client,
        parse_secop_input("CO1.NTC.1234567"),
        process_hits,
        [DATASETS["secop_ii_archivos_2024"]],
    )

    assert process_hits[0]["source_family"] == "SECOP II"
    assert document_hits[0].source_family == "SECOP II"
    assert client.query_calls


def test_inspect_secop_value_happy_path() -> None:
    client: Any = FakeSocrataClient(
        metadata_map={
            dataset_id: _metadata(dataset_id, f"Dataset {index}")
            for index, dataset_id in enumerate(
                [
                    DATASETS["secop_ii_procesos"],
                    DATASETS["secop_i_procesos_desde_2018"],
                    DATASETS["secop_i_procesos_hasta_2017"],
                    DATASETS["secop_ii_archivos_2024"],
                    DATASETS["secop_i_archivos_desde_2019"],
                ],
                start=1,
            )
        },
        process_rows_by_dataset={
            DATASETS["secop_ii_procesos"]: [
                {
                    "id_del_proceso": "CO1.NTC.1234567",
                    "referencia_del_proceso": "REF-2",
                    "entidad": "Entidad II",
                    "nombre_del_procedimiento": "Obra II",
                    "estado_del_procedimiento": "Abierto",
                    "precio_base": "1000",
                    "urlproceso": {"url": "https://example.com/proceso-ii"},
                }
            ]
        },
        document_rows_by_dataset={
            DATASETS["secop_ii_archivos_2024"]: [
                {
                    "proceso": "CO1.NTC.1234567",
                    "id_documento": "DOC-1",
                    "nombre_archivo": "anexo.pdf",
                    "extensi_n": "pdf",
                    "descripci_n": "Anexo",
                    "entidad": "Entidad II",
                    "n_mero_de_contrato": "CT-1",
                    "url_descarga_documento": {"url": "https://example.com/anexo.pdf"},
                }
            ]
        },
    )

    result = inspect_secop_value(client, "CO1.NTC.1234567")

    assert result.parsed_input.platform == "secop_ii"
    assert result.process_rows
    assert result.documents
    assert result.document_groups[0]["source_family"] == "SECOP II"
    assert result.notes == []


def test_inspect_secop_value_empty_input_reports_notes() -> None:
    client: Any = FakeSocrataClient()

    result = inspect_secop_value(client, "   ")

    assert result.parsed_input.input_kind == "empty"
    assert result.process_rows == []
    assert result.documents == []
    assert any("vac" in note.lower() for note in result.notes)
    assert any("plataforma" in note.lower() for note in result.notes)
