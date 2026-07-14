from __future__ import annotations

from business_bridge.adapters.secop_constants import DATASETS
from business_bridge.adapters.secop_models import (
    DatasetMetadataInfo,
    InspectionResult,
    ParsedSecopInput,
)
from business_bridge.adapters.secop_parsing import parse_secop_input
from business_bridge.adapters.secop_render import (
    _render_html_index,
    _render_process_family_summaries,
    _render_process_summary,
    _render_simple_table,
)


def _build_result() -> InspectionResult:
    parsed_input = ParsedSecopInput(
        raw_value="CO1.NTC.1234567",
        input_kind="url",
        platform="secop_ii",
        identifier="CO1.NTC.1234567",
        original_url="https://community.secop.gov.co/Process/NoticeDetail?noticeUID=CO1.NTC.1234567",
        domain="community.secop.gov.co",
        path="/Process/NoticeDetail",
        matched_parameters=("noticeUID",),
        identifier_candidates=("CO1.NTC.1234567",),
    )
    metadata = [
        DatasetMetadataInfo(
            dataset_id=DATASETS["secop_ii_procesos"],
            dataset_name="Procesos SECOP II",
            queried_at="2026-07-12T00:00:00+00:00",
            last_update="2026-07-11T00:00:00+00:00",
            last_update_source="rowsUpdatedAt",
            source_url="https://example.com/secop-ii",
        ),
        DatasetMetadataInfo(
            dataset_id=DATASETS["secop_i_procesos_desde_2018"],
            dataset_name="Procesos SECOP I",
            queried_at="2026-07-12T00:00:00+00:00",
            last_update="2026-07-11T00:00:00+00:00",
            last_update_source="rowsUpdatedAt",
            source_url="https://example.com/secop-i",
        ),
    ]
    process_rows = [
        {
            "source_family": "SECOP II",
            "id_del_proceso": "CO1.NTC.1234567",
            "referencia_del_proceso": "REF-2",
            "entidad": "Entidad II",
            "nombre_del_procedimiento": "Obra II",
            "estado_del_procedimiento": "Abierto",
            "precio_base": "1000",
            "urlproceso": {"url": "https://example.com/proceso-ii"},
        },
        {
            "source_family": "SECOP I",
            "numero_de_constancia": "12-34-567890",
            "numero_de_proceso": "LP-2026-001",
            "nombre_entidad": "Entidad I",
            "objeto_a_contratar": "Obra I",
            "estado_del_proceso": "Cerrado",
            "cuantia_proceso": "2000",
            "ruta_proceso_en_secop_i": {"url": "https://example.com/proceso-i"},
        },
    ]
    return InspectionResult(
        queried_at="2026-07-12T00:00:00+00:00",
        parsed_input=parsed_input,
        metadata=metadata,
        process_rows=process_rows,
        documents=[],
        notes=[],
    )


def test_parse_secop_input_covers_empty_and_reference_cases() -> None:
    empty = parse_secop_input("   ")
    reference = parse_secop_input("LP-2026-001")

    assert empty.input_kind == "empty"
    assert empty.platform == "unknown"
    assert reference.input_kind == "reference"
    assert reference.platform == "unknown"
    assert "generic-reference" in reference.matched_parameters


def test_render_simple_table_and_html_index(monkeypatch) -> None:
    table = _render_simple_table(
        [{"name": "Documento", "url": {"url": "https://example.com/file.pdf"}}],
        ["name", "url"],
    )
    monkeypatch.setattr(
        "business_bridge.adapters.secop_render.workspace_load_index_html",
        lambda: "<html>Business Bridge</html>",
    )

    assert "<table>" in table
    assert "Documento" in table
    assert "https://example.com/file.pdf" in table
    assert _render_html_index() == "<html>Business Bridge</html>"


def test_render_process_summary_and_family_summaries() -> None:
    result = _build_result()

    summary = _render_process_summary(
        InspectionResult(
            queried_at=result.queried_at,
            parsed_input=result.parsed_input,
            metadata=result.metadata,
            process_rows=[
                {
                    "id_del_proceso": "CO1.NTC.1234567",
                    "referencia_del_proceso": "REF-2",
                    "entidad": "Entidad II",
                    "nombre_del_procedimiento": "Obra II",
                    "estado_del_procedimiento": "Abierto",
                    "precio_base": "1000",
                    "urlproceso": {"url": "https://example.com/proceso-ii"},
                }
            ],
            documents=[],
        )
    )
    family_summaries = _render_process_family_summaries(result)

    assert summary["dataset_id"] == DATASETS["secop_ii_procesos"]
    assert summary["process_id"] == "CO1.NTC.1234567"
    assert summary["document_url"] == "https://example.com/proceso-ii"
    assert family_summaries[0]["source_family"] == "SECOP I"
    assert family_summaries[0]["process_count"] == 1
    assert family_summaries[1]["source_family"] == "SECOP II"
    assert family_summaries[1]["process_count"] == 1
