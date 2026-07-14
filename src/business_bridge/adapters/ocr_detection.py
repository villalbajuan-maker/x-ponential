from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple
from uuid import uuid4

from business_bridge.adapters.ocr_extractors import extract_text_from_file
from business_bridge.adapters.ocr_text import clean_value, normalize_text, safe_preview


TENDER_EXPECTED_FIELDS = [
    "tender.process_number",
    "tender.entity",
    "tender.offer_value",
    "tender.execution_term",
    "tender.date",
]

REUSABLE_FIELD_KEYS = {"company.nit", "company.email", "company.phone"}


def clean_extracted_pages(page_texts: Sequence[str]) -> List[str]:
    """Normalizar cada pagina extraida antes de que la inspeccionen las reglas regex."""

    return [normalize_text(text) for text in page_texts]


def add_detected_item(
    items: List[Dict[str, Any]],
    seen_values: set[Tuple[str, str]],
    field_key: str,
    label: str,
    value: str,
    confidence: float,
    page: Optional[int],
    reusable: bool = False,
    source: str = "regex",
) -> None:
    """Agregar un campo detectado solo si pasa validaciones basicas."""

    cleaned_value = clean_value(value)
    if not cleaned_value:
        return
    digit_count = len(re.sub(r"\D", "", cleaned_value))
    if field_key == "company.phone" and digit_count < 7:
        return
    if field_key == "company.nit" and digit_count < 5:
        return
    if field_key == "company.phone":
        if digit_count < 10 or digit_count > 15:
            return
        if re.search(
            r"\b(?:nit|proceso|oferta|valor|precio|fecha)\b", cleaned_value, re.IGNORECASE
        ):
            return
    if field_key == "tender.process_number" and digit_count < 3:
        return
    seen_key = (field_key, cleaned_value.casefold())
    if seen_key in seen_values:
        return
    seen_values.add(seen_key)
    items.append(
        {
            "item_id": f"item_{uuid4().hex}",
            "field_key": field_key,
            "label": label,
            "value": cleaned_value,
            "confidence": round(confidence, 2),
            "source": source,
            "page": page,
            "status": "pending_review",
            "reusable": reusable,
        }
    )


def extract_regex_items(page_texts: Sequence[str]) -> List[Dict[str, Any]]:
    """Encontrar campos estructurados con un conjunto pequeno de reglas regex de alto valor."""

    items: List[Dict[str, Any]] = []
    seen_values: set[Tuple[str, str]] = set()

    regex_specs = [
        (
            "company.nit",
            "NIT",
            [
                re.compile(r"\bNIT\s*[:\-]?\s*([0-9][0-9.\-]{4,20})\b", re.IGNORECASE),
                re.compile(r"\b([0-9]{3,15}(?:\.[0-9]{3}){1,3}-[0-9])\b"),
            ],
            0.95,
            True,
        ),
        (
            "company.email",
            "Correo",
            [re.compile(r"\b([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})\b")],
            0.98,
            True,
        ),
        (
            "company.phone",
            "Telefono",
            [
                re.compile(
                    r"(?:tel[e\u00e9]fono|celular|mov[i\u00ed]l|phone)\s*[:\-]?\s*([+()0-9\s.-]{7,20})",
                    re.IGNORECASE,
                ),
            ],
            0.9,
            True,
        ),
        (
            "tender.offer_value",
            "Valor posible",
            [
                re.compile(
                    r"(?:valor(?: total)?(?: de la oferta)?|oferta|precio)\s*[:\-]?\s*((?:COP\s*)?\$?\s*\d{1,3}(?:[.\s]\d{3})+(?:,\d{1,2})?)",
                    re.IGNORECASE,
                ),
            ],
            0.9,
            False,
        ),
        (
            "tender.date",
            "Fecha",
            [
                re.compile(r"\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b"),
                re.compile(r"\b(\d{4}[/-]\d{1,2}[/-]\d{1,2})\b"),
                re.compile(
                    r"\b(\d{1,2}\s+de\s+(?:enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|setiembre|octubre|noviembre|diciembre)\s+de\s+\d{4})\b",
                    re.IGNORECASE,
                ),
            ],
            0.9,
            False,
        ),
        (
            "tender.process_number",
            "Numero de proceso",
            [
                re.compile(
                    r"(?:proceso(?: de selecci[o\u00f3]n)?|n[u\u00fa]mero de proceso|radicado|no\.?|nro\.?)\s*[:\-]?\s*([A-Z0-9][A-Z0-9\-\/._]{2,80})",
                    re.IGNORECASE,
                ),
                re.compile(
                    r"\b(?:SECOP|LP|MC|CD|CM|SA|IP)\s*[-/ ]?[A-Z0-9][A-Z0-9\-\/._]{2,40}\b",
                    re.IGNORECASE,
                ),
            ],
            0.86,
            False,
        ),
        (
            "tender.entity",
            "Entidad",
            [
                re.compile(
                    r"(?:entidad(?: contratante)?|nombre de la entidad|entidad responsable)\s*[:\-]\s*([^\n\r]{3,120})",
                    re.IGNORECASE,
                )
            ],
            0.82,
            False,
        ),
        (
            "tender.execution_term",
            "Plazo de ejecucion",
            [
                re.compile(
                    r"(?:plazo de ejecuci[o\u00f3]n|duraci[o\u00f3]n|tiempo de ejecuci[o\u00f3]n)\s*[:\-]?\s*([^\n\r]{3,80})",
                    re.IGNORECASE,
                ),
                re.compile(
                    r"\bplazo\b\s*[:\-]?\s*([0-9]{1,3}\s*(?:d[i\u00ed]as?|meses?|semanas?)[^\n\r]*)",
                    re.IGNORECASE,
                ),
            ],
            0.8,
            False,
        ),
    ]

    for page_index, page_text in enumerate(page_texts, start=1):
        text = normalize_text(page_text)
        if not text:
            continue
        for field_key, label, patterns, confidence, reusable in regex_specs:
            for pattern in patterns:
                for match in pattern.finditer(text):
                    candidate = match.group(1) if match.groups() else match.group(0)
                    add_detected_item(
                        items=items,
                        seen_values=seen_values,
                        field_key=field_key,
                        label=label,
                        value=candidate,
                        confidence=confidence,
                        page=page_index if len(page_texts) > 1 else None,
                        reusable=reusable or field_key in REUSABLE_FIELD_KEYS,
                    )

    return items


def calculate_overall_confidence(
    detected_items: Sequence[Dict[str, Any]], document_type: str, raw_text: str
) -> float:
    """Colapsar la confianza por item en una sola puntuacion de documento."""

    if detected_items:
        average_confidence = sum(float(item.get("confidence", 0.0)) for item in detected_items)
        average_confidence /= len(detected_items)
        if document_type in {"pdf_scanned", "image"}:
            average_confidence -= 0.05
        return round(max(0.0, min(0.99, average_confidence)), 2)
    if raw_text.strip():
        return 0.45 if document_type in {"pdf_scanned", "image"} else 0.5
    return 0.0


def build_extraction_record(stored_file: Path, document_id: Optional[str] = None) -> Dict[str, Any]:
    """Armar el registro persistido que usa el flujo de revision del frontend."""

    stored_file = Path(stored_file)
    if document_id is None:
        document_id = stored_file.name.split("__", 1)[0]
    original_file_name = (
        stored_file.name.split("__", 1)[1] if "__" in stored_file.name else stored_file.name
    )
    page_texts, file_type, document_type, warnings = extract_text_from_file(stored_file)
    cleaned_page_texts = clean_extracted_pages(page_texts)
    combined_text = "\n".join(text for text in cleaned_page_texts if text).strip()
    detected_items = extract_regex_items(cleaned_page_texts)
    detected_field_keys = {item["field_key"] for item in detected_items}
    missing_fields = [
        field_key for field_key in TENDER_EXPECTED_FIELDS if field_key not in detected_field_keys
    ]

    if not combined_text and not warnings:
        warnings.append("No text could be extracted from the document.")
    elif not combined_text:
        warnings.append("Extraction completed but no usable text was found.")

    return {
        "document_id": document_id,
        "file_name": original_file_name,
        "file_type": file_type,
        "document_type": document_type,
        "confidence": calculate_overall_confidence(detected_items, document_type, combined_text),
        "raw_text_preview": safe_preview(combined_text),
        "detected_items": detected_items,
        "missing_fields": missing_fields,
        "warnings": warnings,
        "supplemental_answers": {},
    }
