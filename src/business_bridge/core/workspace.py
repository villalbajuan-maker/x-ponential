from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict
from uuid import uuid4

from fastapi import HTTPException, UploadFile

REPO_ROOT = Path(__file__).resolve().parents[3]
API_STATIC_DIR = REPO_ROOT / "src" / "business_bridge" / "api" / "static"
INDEX_FILE = API_STATIC_DIR / "index.html"
COMPANY_ROOT = REPO_ROOT / "company" / "Business_Bridge"
ORIGINALS_DIR = COMPANY_ROOT / "originales"
ACTUALIZADOS_DIR = COMPANY_ROOT / "actualizados"
COMPANY_PROFILE_FILE = COMPANY_ROOT / "data.json"
EXTRACTION_FILE_SUFFIX = "__extraction.json"


def ensure_company_layout() -> None:
    """Crear la estructura local de empresa usada por el piloto."""

    for folder in (COMPANY_ROOT, ORIGINALS_DIR, ACTUALIZADOS_DIR):
        folder.mkdir(parents=True, exist_ok=True)


def company_layout_is_ready() -> bool:
    """Comprobar si existen las carpetas y el archivo de perfil esperados."""

    return (
        all(folder.exists() for folder in (COMPANY_ROOT, ORIGINALS_DIR, ACTUALIZADOS_DIR))
        and COMPANY_PROFILE_FILE.exists()
    )


def load_index_html(index_file: Path = INDEX_FILE) -> str:
    """Cargar el HTML del frontend desde disco o devolver una pagina minima de respaldo."""

    if index_file.exists():
        return index_file.read_text(encoding="utf-8")

    return """\
<!doctype html>
<html lang="es">
  <head><meta charset="utf-8"><title>Business Bridge</title></head>
  <body>
    <h1>Business Bridge</h1>
    <p>index.html no fue encontrado.</p>
  </body>
</html>
"""


def normalize_uploaded_filename(filename: str) -> str:
    """Convertir un nombre subido en uno seguro para el sistema de archivos."""

    base_name = Path(filename).name.strip().replace(" ", "_")
    safe_name = re.sub(r"[^A-Za-z0-9._-]+", "-", base_name).strip("._-")
    return safe_name or "documento"


def build_document_id() -> str:
    """Generar un identificador unico para un documento almacenado."""

    return f"doc_{uuid4().hex}"


def detect_file_type(filename: str) -> str:
    """Inferir el tipo de archivo a partir de la extension del nombre."""

    suffix = Path(filename).suffix.lower().lstrip(".")
    return suffix or "unknown"


def build_uploaded_filename(document_id: str, original_file_name: str) -> str:
    """Unir el id del documento y el nombre original en el archivo guardado."""

    return f"{document_id}__{normalize_uploaded_filename(original_file_name)}"


def find_uploaded_file(document_id: str) -> Path:
    """Encontrar el unico archivo guardado que corresponde a un document_id."""

    matches = sorted(ORIGINALS_DIR.glob(f"{document_id}__*"))
    if not matches:
        raise FileNotFoundError(f"Document not found: {document_id}")
    return matches[0]


def get_original_file_name(stored_file_name: str) -> str:
    """Recuperar el nombre original desde el formato con prefijo almacenado."""

    return stored_file_name.split("__", 1)[1] if "__" in stored_file_name else stored_file_name


def get_extraction_file_path(document_id: str) -> Path:
    """Devolver la ruta sidecar donde se guarda el JSON de extraccion."""

    return ACTUALIZADOS_DIR / f"{document_id}{EXTRACTION_FILE_SUFFIX}"


def decode_uploaded_json(upload_file: UploadFile) -> Dict[str, Any]:
    """Decodificar un archivo subido como JSON con respaldo de codificaciones."""

    raw_bytes = upload_file.file.read()
    if not raw_bytes:
        raise HTTPException(status_code=400, detail="The selected JSON file is empty.")

    decoded_text = None
    for encoding in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            decoded_text = raw_bytes.decode(encoding)
            break
        except UnicodeDecodeError:
            continue

    if decoded_text is None:
        raise HTTPException(
            status_code=400, detail="The selected file could not be decoded as JSON."
        )

    try:
        payload = json.loads(decoded_text)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="The selected file is not valid JSON.") from exc

    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="The imported JSON must be an object.")

    return payload
