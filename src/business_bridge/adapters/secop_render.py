from __future__ import annotations

import html
import json
from typing import Any, Dict, Mapping, Sequence

from business_bridge.adapters.secop_constants import DATASETS
from business_bridge.adapters.secop_models import InspectionResult
from business_bridge.adapters.secop_flow import _metadata_by_dataset_id, _process_summary_from_row
from business_bridge.adapters.secop_utils import _first_non_empty
from business_bridge.core.workspace import load_index_html as workspace_load_index_html


def _render_simple_table(rows: Sequence[Mapping[str, Any]], keys: Sequence[str]) -> str:
    """Renderizar una tabla HTML compacta a partir de una lista de mapas."""

    if not rows:
        return "<div class='empty'>Sin filas.</div>"
    header = "".join(f"<th>{html.escape(key)}</th>" for key in keys)
    body_rows = []
    for row in rows:
        cells = []
        for key in keys:
            value = row.get(key, "")
            if isinstance(value, dict):
                value = value.get("url", json.dumps(value, ensure_ascii=False))
            cells.append(f"<td>{html.escape(_first_non_empty(value))}</td>")
        body_rows.append("<tr>" + "".join(cells) + "</tr>")
    return "<table><thead><tr>%s</tr></thead><tbody>%s</tbody></table>" % (
        header,
        "".join(body_rows),
    )


def _render_process_summary(result: InspectionResult) -> Dict[str, Any]:
    """Devolver un resumen unico de proceso para la primera fila coincidente."""

    if not result.process_rows:
        return {}
    first_row = result.process_rows[0]
    dataset_id = _first_non_empty(first_row.get("dataset_id")) or (
        DATASETS["secop_ii_procesos"]
        if result.parsed_input.platform == "secop_ii"
        else DATASETS["secop_i_procesos_desde_2018"]
    )
    matched_metadata = next(
        (meta for meta in result.metadata if meta.dataset_id == dataset_id), None
    )
    dataset_name = matched_metadata.dataset_name if matched_metadata is not None else dataset_id
    return _process_summary_from_row(dataset_id, first_row, dataset_name)


def _render_process_family_summaries(result: InspectionResult) -> list[Dict[str, Any]]:
    """Devolver un resumen por familia SECOP para que la UI pinte ambas columnas."""

    metadata_by_id = _metadata_by_dataset_id(result.metadata)
    family_index: Dict[str, list[Dict[str, Any]]] = {}

    for row in result.process_rows:
        family = _first_non_empty(row.get("source_family")) or (
            "SECOP II"
            if _first_non_empty(row.get("dataset_id")) == DATASETS["secop_ii_procesos"]
            else "SECOP I"
        )
        family_index.setdefault(family, []).append(row)

    summaries: list[Dict[str, Any]] = []
    for family in ("SECOP I", "SECOP II"):
        rows = family_index.get(family, [])
        if rows:
            first_row = rows[0]
            dataset_id = _first_non_empty(first_row.get("dataset_id")) or (
                DATASETS["secop_ii_procesos"]
                if family == "SECOP II"
                else DATASETS["secop_i_procesos_desde_2018"]
            )
            metadata = metadata_by_id.get(dataset_id)
            dataset_name = metadata.dataset_name if metadata is not None else dataset_id
            summary = _process_summary_from_row(dataset_id, first_row, dataset_name)
            summary["source_family"] = family
            summary["process_count"] = len(rows)
            summaries.append(summary)
        else:
            summaries.append(
                {
                    "source_family": family,
                    "process_count": 0,
                    "dataset_id": "",
                    "dataset_name": "",
                    "process_id": "",
                    "reference": "",
                    "entity": "",
                    "title": "",
                    "status": "",
                    "amount": "",
                    "document_url": "",
                }
            )

    extra_families = [family for family in family_index if family not in {"SECOP I", "SECOP II"}]
    for family in extra_families:
        rows = family_index.get(family, [])
        first_row = rows[0]
        dataset_id = _first_non_empty(first_row.get("dataset_id"))
        metadata = metadata_by_id.get(dataset_id)
        dataset_name = metadata.dataset_name if metadata is not None else dataset_id
        summary = _process_summary_from_row(dataset_id, first_row, dataset_name)
        summary["source_family"] = family
        summary["process_count"] = len(rows)
        summaries.append(summary)

    return summaries


def _render_html_index() -> str:
    """Devolver el contenedor HTML local usado por el servidor del inspector embebido."""

    return workspace_load_index_html()
