from __future__ import annotations

import re
import unicodedata
from pathlib import Path
from typing import Any

from business_bridge.core.workspace import detect_file_type as workspace_detect_file_type

detect_file_type = workspace_detect_file_type


def normalize_text(text: str) -> str:
    """Normalizar Unicode y espacios para que el parseo vea una forma estable."""

    if not text:
        return ""
    normalized = unicodedata.normalize("NFKC", text)
    normalized = normalized.replace("\r\n", "\n").replace("\r", "\n").replace("\xa0", " ")
    normalized = re.sub(r"-\n(?=\w)", "", normalized)
    normalized = re.sub(r"[ \t]+", " ", normalized)
    normalized = re.sub(r"\n{3,}", "\n\n", normalized)
    normalized = "\n".join(line.strip() for line in normalized.split("\n"))
    return normalized.strip()


def safe_preview(text: str, limit: int = 1000) -> str:
    """Devolver una vista previa compacta y limpia de un texto largo."""

    cleaned = normalize_text(text)
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[:limit].rstrip() + "..."


def clean_value(value: Any) -> str:
    """Reducir un valor escalar a una representacion segura de una sola linea."""

    return re.sub(r"\s+", " ", str(value)).strip(" \t\n\r;,.:-")


def read_text_file(path: Path) -> str:
    """Leer un archivo de texto probando UTF-8 primero y Latin-1 como respaldo."""

    try:
        return path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        return path.read_text(encoding="latin-1", errors="ignore")
