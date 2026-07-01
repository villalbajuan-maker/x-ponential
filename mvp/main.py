from __future__ import annotations

import json
import re
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple
from uuid import uuid4

# Preferimos las importaciones de paquete, pero caemos a ejecucion local cuando el modulo corre desde `mvp/`.
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

try:
    from mvp.ocr import (
        TENDER_EXPECTED_FIELDS,
        build_extraction_record as ocr_build_extraction_record,
        clean_value as ocr_clean_value,
        detect_file_type as ocr_detect_file_type,
    )
    from mvp.secop import secop_router
except ModuleNotFoundError:
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from ocr import (
        TENDER_EXPECTED_FIELDS,
        build_extraction_record as ocr_build_extraction_record,
        clean_value as ocr_clean_value,
        detect_file_type as ocr_detect_file_type,
    )
    from secop import secop_router


# ============================================================
# Importaciones y configuracion
# ============================================================

# El MVP guarda su frontend y el espacio de trabajo de empresa junto a este archivo.
BASE_DIR = Path(__file__).resolve().parent
INDEX_FILE = BASE_DIR / "index.html"
COMPANY_ROOT = BASE_DIR / "company" / "SEASIM"
ORIGINALS_DIR = COMPANY_ROOT / "originales"
ACTUALIZADOS_DIR = COMPANY_ROOT / "actualizados"
COMPANY_PROFILE_FILE = COMPANY_ROOT / "data.json"

APP_NAME = "OCR Licitaciones MVP"
APP_VERSION = "0.5.0"
CHECKPOINT = "5"

DEFAULT_COMPANY_PROFILE: Dict[str, str] = {
    "business_name": "",
    "nit": "",
    "legal_representative": "",
    "legal_representative_id": "",
    "address": "",
    "city": "",
    "phone": "",
    "email": "",
    "bank_name": "",
    "bank_account_type": "",
    "bank_account_number": "",
}

COMPANY_PROFILE_FIELDS = set(DEFAULT_COMPANY_PROFILE.keys())
ALLOWED_MISSING_FIELD_KEYS = set(TENDER_EXPECTED_FIELDS) | COMPANY_PROFILE_FIELDS
REVIEW_STATUSES = {"pending_review", "accepted", "edited", "discarded"}
COMPANY_PROFILE_REVIEW_MAP = {
    "company.nit": "nit",
    "company.email": "email",
    "company.phone": "phone",
}
EXTRACTION_FILE_SUFFIX = "__extraction.json"

# Una sola aplicacion de FastAPI sirve el frontend HTML y la API de OCR/SECOP.
app = FastAPI(title=APP_NAME, version=APP_VERSION)
app.include_router(secop_router)


# ============================================================
# Preparacion del espacio de trabajo de empresa
# ============================================================

def ensure_company_layout() -> None:
    """Crear la estructura local de empresa usada por el MVP."""

    for folder in (COMPANY_ROOT, ORIGINALS_DIR, ACTUALIZADOS_DIR):
        folder.mkdir(parents=True, exist_ok=True)


def default_company_profile() -> Dict[str, str]:
    """Devolver un perfil de empresa vacío y limpio."""
    return dict(DEFAULT_COMPANY_PROFILE)


def normalize_company_profile(raw_profile: Dict[str, Any]) -> Dict[str, str]:
    """Convertir cualquier perfil compatible al esquema canónico de cadenas."""
    normalized = default_company_profile()
    source_profile: Dict[str, Any] = raw_profile
    if isinstance(raw_profile.get("company_profile"), dict):
        source_profile = raw_profile["company_profile"]
    for field_name in normalized:
        value = source_profile.get(field_name, raw_profile.get(field_name, normalized[field_name]))
        normalized[field_name] = "" if value is None else str(value)
    return normalized


def ensure_company_profile_file() -> None:
    """Crear el archivo JSON del perfil en disco si todavia no existe."""
    ensure_company_layout()
    if COMPANY_PROFILE_FILE.exists():
        return
    COMPANY_PROFILE_FILE.write_text(
        json.dumps(default_company_profile(), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def load_company_profile_raw() -> Dict[str, Any]:
    """Leer el JSON crudo del perfil sin asumir un esquema rigido."""
    ensure_company_profile_file()
    try:
        raw_profile = json.loads(COMPANY_PROFILE_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        raw_profile = {}
    if not isinstance(raw_profile, dict):
        raw_profile = {}
    return raw_profile


def load_company_profile() -> Dict[str, str]:
    """Devolver el perfil de empresa normalizado que usa la API."""
    return normalize_company_profile(load_company_profile_raw())


def save_company_profile(profile_data: Dict[str, Any]) -> Dict[str, str]:
    """Fusionar los datos nuevos del perfil con lo que ya esta guardado."""
    existing_profile = load_company_profile_raw()
    normalized_profile = normalize_company_profile(profile_data)
    # Primero normalizamos el aporte nuevo y luego lo mezclamos con el archivo persistido.
    merged_profile: Dict[str, Any] = dict(existing_profile)
    merged_profile.update(normalized_profile)
    COMPANY_PROFILE_FILE.write_text(
        json.dumps(merged_profile, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return normalize_company_profile(merged_profile)


def decode_uploaded_json(upload_file: UploadFile) -> Dict[str, Any]:
    """Decodificar un archivo subido como JSON con un pequeno respaldo de codificaciones."""
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
        raise HTTPException(status_code=400, detail="The selected file could not be decoded as JSON.")

    try:
        payload = json.loads(decoded_text)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="The selected file is not valid JSON.") from exc

    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="The imported JSON must be an object.")

    return payload


def import_company_profile_payload(payload: Dict[str, Any]) -> Tuple[Dict[str, Any], List[str]]:
    """Fusionar un perfil importado dentro del perfil de empresa guardado."""
    existing_profile = load_company_profile_raw()
    merged_profile: Dict[str, Any] = dict(existing_profile)
    imported_keys: List[str] = []

    # Si el archivo trae un envoltorio company_profile, separamos los campos extra del perfil canonico.
    if isinstance(payload.get("company_profile"), dict):
        company_payload = payload["company_profile"]
        extra_payload = {key: value for key, value in payload.items() if key != "company_profile"}
        merged_profile.update(extra_payload)
        normalized_profile = normalize_company_profile(company_payload)
        imported_keys.extend([key for key in normalized_profile if normalized_profile[key]])
        merged_profile.update(normalized_profile)
    else:
        # Si llega un JSON plano, lo tratamos como perfil directo y tambien guardamos el aporte original.
        normalized_profile = normalize_company_profile(payload)
        imported_keys.extend([key for key in normalized_profile if normalized_profile[key]])
        merged_profile.update(payload)
        merged_profile.update(normalized_profile)

    COMPANY_PROFILE_FILE.write_text(
        json.dumps(merged_profile, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return merged_profile, imported_keys


@app.on_event("startup")
def startup_event() -> None:
    """Levantar el espacio de trabajo de empresa antes de servir la primera peticion."""
    ensure_company_layout()
    ensure_company_profile_file()


# ============================================================
# Esquemas Pydantic
# ============================================================

class HealthResponse(BaseModel):
    """Respuesta del health check del servicio FastAPI."""
    status: str
    app_name: str
    version: str
    checkpoint: str
    company_ready: bool


class CompanyProfile(BaseModel):
    """Perfil canonico de empresa almacenado por el MVP."""
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


CompanyProfile.model_rebuild()
CompanyProfileEnvelope.model_rebuild()
CompanyProfileImportEnvelope.model_rebuild()


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


# ============================================================
# Funciones de apoyo
# ============================================================

def load_index_html() -> str:
    """Cargar el HTML del frontend desde disco o devolver una pagina minima de respaldo."""
    if INDEX_FILE.exists():
        return INDEX_FILE.read_text(encoding="utf-8")

    # Si no existe el index local, servimos una pagina minima para que la app siga levantando.
    return """
    <!doctype html>
    <html lang="es">
      <head><meta charset="utf-8"><title>OCR Licitaciones MVP</title></head>
      <body>
        <h1>OCR Licitaciones MVP</h1>
        <p>index.html no fue encontrado.</p>
      </body>
    </html>
    """


def company_layout_is_ready() -> bool:
    """Comprobar si existen las carpetas y el archivo de perfil esperados."""
    return all(folder.exists() for folder in (COMPANY_ROOT, ORIGINALS_DIR, ACTUALIZADOS_DIR)) and COMPANY_PROFILE_FILE.exists()


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


def normalize_text(text: str) -> str:
    """Normalizar Unicode, espacios y saltos de línea para el parseo posterior."""
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
    """Devolver una vista previa limpia y truncada a una longitud segura."""
    cleaned = normalize_text(text)
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[:limit].rstrip() + "..."


def clean_value(value: str) -> str:
    """Normalizar un valor escalar para comparación y almacenamiento."""
    return re.sub(r"\s+", " ", str(value)).strip(" \t\n\r;,.:-")


def read_text_file(path: Path) -> str:
    """Leer un archivo de texto intentando UTF-8 primero y Latin-1 después."""
    try:
        return path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        return path.read_text(encoding="latin-1", errors="ignore")


def extract_pdf_page_texts(path: Path) -> List[str]:
    """Extraer el texto incrustado de cada pagina de un PDF."""
    page_texts: List[str] = []
    with fitz.open(path) as pdf_document:
        for page in pdf_document:
            page_texts.append(page.get_text("text") or "")
    return page_texts


def render_pdf_page_to_image(page: fitz.Page) -> Image.Image:
    """Renderizar una página PDF como imagen raster para OCR."""
    pixmap = page.get_pixmap(matrix=fitz.Matrix(2.0, 2.0), alpha=False)
    return Image.frombytes("RGB", [pixmap.width, pixmap.height], pixmap.samples)


def preprocess_image_for_ocr(image: Image.Image) -> Image.Image:
    """Binarizar una imagen para mejorar la legibilidad del OCR."""
    grayscale = image.convert("L")
    thresholded = grayscale.point(lambda pixel: 255 if pixel > 180 else 0)
    return thresholded


def run_ocr(image: Image.Image) -> Tuple[str, List[str]]:
    """Ejecutar OCR y recolectar advertencias no fatales."""
    warnings: List[str] = []
    try:
        text = pytesseract.image_to_string(image, config="--psm 6")
    except TesseractNotFoundError:
        warnings.append("Tesseract executable not found; OCR was skipped.")
        return "", warnings
    except Exception as exc:  # pragma: no cover - safety net for OCR engines
        warnings.append(f"OCR failed: {exc}")
        return "", warnings

    return normalize_text(text), warnings


def extract_text_from_pdf(path: Path) -> Tuple[List[str], str, List[str]]:
    """Extraer texto del PDF directamente o caer en OCR si hace falta."""
    warnings: List[str] = []
    page_texts = extract_pdf_page_texts(path)
    combined_text = "\n".join(page_texts).strip()

    if combined_text:
        return [normalize_text(text) for text in page_texts], "pdf_editable", warnings

    ocr_page_texts: List[str] = []
    with fitz.open(path) as pdf_document:
        for page_number, page in enumerate(pdf_document, start=1):
            image = render_pdf_page_to_image(page)
            processed_image = preprocess_image_for_ocr(image)
            page_text, ocr_warnings = run_ocr(processed_image)
            warnings.extend([f"Page {page_number}: {warning}" for warning in ocr_warnings])
            if page_text:
                ocr_page_texts.append(page_text)
            else:
                ocr_page_texts.append("")

    warnings.append("OCR applied because the PDF did not contain embedded text.")
    return ocr_page_texts, "pdf_scanned", warnings


def extract_text_from_image(path: Path) -> Tuple[List[str], str, List[str]]:
    """Ejecutar OCR sobre una sola imagen."""
    image = Image.open(path)
    processed_image = preprocess_image_for_ocr(image)
    text, warnings = run_ocr(processed_image)
    return [text], "image", warnings


def extract_text_from_docx(path: Path) -> Tuple[List[str], str, List[str]]:
    """Extraer el texto visible de parrafos y tablas de un DOCX."""
    warnings: List[str] = []
    document = Document(path)
    lines: List[str] = []

    for paragraph in document.paragraphs:
        if paragraph.text.strip():
            lines.append(paragraph.text)

    for table in document.tables:
        for row in table.rows:
            row_values = [cell.text.strip() for cell in row.cells if cell.text.strip()]
            if row_values:
                lines.append(" | ".join(row_values))

    return [normalize_text("\n".join(lines))], "docx", warnings


def extract_text_from_csv(path: Path) -> Tuple[List[str], str, List[str]]:
    """Leer un CSV y aplanarlo en texto normalizado."""
    warnings: List[str] = []
    try:
        dataframe = pd.read_csv(path, dtype=str, keep_default_na=False, sep=None, engine="python")
    except Exception:
        dataframe = pd.read_csv(path, dtype=str, keep_default_na=False, encoding="latin-1", sep=None, engine="python")

    text = dataframe.to_csv(index=False)
    return [normalize_text(text)], "csv", warnings


def extract_text_from_xlsx(path: Path) -> Tuple[List[str], str, List[str]]:
    """Leer cada hoja de un XLSX como texto plano."""
    warnings: List[str] = []
    workbook = load_workbook(path, data_only=True, read_only=True)
    lines: List[str] = []

    for worksheet in workbook.worksheets:
        lines.append(f"[Sheet] {worksheet.title}")
        for row in worksheet.iter_rows(values_only=True):
            row_values = [clean_value(cell) for cell in row if cell is not None and clean_value(cell) != ""]
            if row_values:
                lines.append("\t".join(row_values))

    workbook.close()
    return [normalize_text("\n".join(lines))], "xlsx", warnings


def extract_text_from_file(path: Path) -> Tuple[List[str], str, str, List[str]]:
    """Despachar la extraccion de texto segun la extension del archivo."""
    ext = path.suffix.lower()
    warnings: List[str] = []
    file_type = ext.lstrip(".") or "unknown"

    try:
        if ext == ".pdf":
            page_texts, document_type, pdf_warnings = extract_text_from_pdf(path)
            warnings.extend(pdf_warnings)
            return page_texts, file_type, document_type, warnings

        if ext in SUPPORTED_IMAGE_EXTENSIONS:
            page_texts, document_type, image_warnings = extract_text_from_image(path)
            warnings.extend(image_warnings)
            return page_texts, file_type, document_type, warnings

        if ext == ".txt":
            return [normalize_text(read_text_file(path))], file_type, "txt", warnings

        if ext == ".csv":
            page_texts, document_type, csv_warnings = extract_text_from_csv(path)
            warnings.extend(csv_warnings)
            return page_texts, file_type, document_type, warnings

        if ext == ".docx":
            page_texts, document_type, docx_warnings = extract_text_from_docx(path)
            warnings.extend(docx_warnings)
            return page_texts, file_type, document_type, warnings

        if ext == ".xlsx":
            page_texts, document_type, xlsx_warnings = extract_text_from_xlsx(path)
            warnings.extend(xlsx_warnings)
            return page_texts, file_type, document_type, warnings

        if ext in UNSUPPORTED_EXTENSIONS:
            warnings.append("XLSB files are not supported in this MVP yet.")
            return [""], file_type, "unsupported_xlsb", warnings

        warnings.append(f"Unsupported file type: {ext.lstrip('.') or 'unknown'}.")
        return [""], file_type, "unsupported", warnings
    except Exception as exc:
        warnings.append(f"Extraction failed for .{file_type} files: {exc}")
        return [""], file_type, f"error_{file_type}", warnings


def clean_extracted_pages(page_texts: Sequence[str]) -> List[str]:
    """Normalizar cada página extraída antes de la extracción por regex."""
    return [normalize_text(text) for text in page_texts]


def add_detected_item(
    items: List[DetectedItem],
    seen_values: set[Tuple[str, str]],
    field_key: str,
    label: str,
    value: str,
    confidence: float,
    page: Optional[int],
    reusable: bool = False,
    source: str = "regex",
) -> None:
    """Agregar un campo detectado solo cuando pasa deduplicacion y validaciones basicas."""
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
        if re.search(r"\b(?:nit|proceso|oferta|valor|precio|fecha)\b", cleaned_value, re.IGNORECASE):
            return
    if field_key == "tender.process_number" and digit_count < 3:
        return
    seen_key = (field_key, cleaned_value.casefold())
    if seen_key in seen_values:
        return
    seen_values.add(seen_key)
    items.append(
        DetectedItem(
            item_id=f"item_{uuid4().hex}",
            field_key=field_key,
            label=label,
            value=cleaned_value,
            confidence=round(confidence, 2),
            source=source,
            page=page,
            status="pending_review",
            reusable=reusable,
        )
    )


def extract_regex_items(page_texts: Sequence[str]) -> List[DetectedItem]:
    """Extraer candidatos estructurados desde las paginas de texto limpiado."""
    items: List[DetectedItem] = []
    seen_values: set[Tuple[str, str]] = set()

    # Estos patrones capturan los campos que el MVP reconoce con alta confianza.
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
                re.compile(r"(?:tel[e\u00e9]fono|celular|mov[i\u00ed]l|phone)\s*[:\-]?\s*([+()0-9\s.-]{7,20})", re.IGNORECASE),
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
                re.compile(r"\b(?:SECOP|LP|MC|CD|CM|SA|IP)\s*[-/ ]?[A-Z0-9][A-Z0-9\-\/._]{2,40}\b", re.IGNORECASE),
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

    # Escaneamos cada pagina por separado para deduplicar valores repetidos con seguridad.
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

def calculate_overall_confidence(detected_items: Sequence[DetectedItem], document_type: str, raw_text: str) -> float:
    """Colapsar la confianza por item en una sola puntuacion de documento."""
    if detected_items:
        average_confidence = sum(item.confidence for item in detected_items) / len(detected_items)
        if document_type in {"pdf_scanned", "image"}:
            average_confidence -= 0.05
        return round(max(0.0, min(0.99, average_confidence)), 2)
    if raw_text.strip():
        return 0.45 if document_type in {"pdf_scanned", "image"} else 0.5
    return 0.0


def build_extraction_record(document_id: str) -> DocumentExtractionRecord:
    """Armar el payload de extraccion que la UI revisa y guarda."""
    stored_file = find_uploaded_file(document_id)
    original_file_name = get_original_file_name(stored_file.name)
    page_texts, file_type, document_type, warnings = extract_text_from_file(stored_file)
    cleaned_page_texts = clean_extracted_pages(page_texts)
    combined_text = "\n".join(text for text in cleaned_page_texts if text).strip()
    detected_items = extract_regex_items(cleaned_page_texts)
    # Todo lo que siga faltando despues de la regex se muestra de vuelta en la UI de revision.
    detected_field_keys = {item.field_key for item in detected_items}
    missing_fields = [field_key for field_key in TENDER_EXPECTED_FIELDS if field_key not in detected_field_keys]

    if not combined_text and not warnings:
        warnings.append("No text could be extracted from the document.")
    elif not combined_text:
        warnings.append("Extraction completed but no usable text was found.")

    extraction_record = DocumentExtractionRecord(
        document_id=document_id,
        file_name=original_file_name,
        file_type=file_type,
        document_type=document_type,
        confidence=calculate_overall_confidence(detected_items, document_type, combined_text),
        raw_text_preview=safe_preview(combined_text),
        detected_items=detected_items,
        missing_fields=missing_fields,
        warnings=warnings,
    )
    return extraction_record


def save_extraction_record(record: DocumentExtractionRecord) -> Path:
    """Persistir el registro de extraccion como un JSON sidecar."""
    path = get_extraction_file_path(record.document_id)
    path.write_text(json.dumps(record.model_dump(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def load_extraction_record(document_id: str) -> DocumentExtractionRecord:
    """Cargar desde disco un registro de extraccion guardado previamente."""
    path = get_extraction_file_path(document_id)
    if not path.exists():
        raise FileNotFoundError(f"Extraction not found for document: {document_id}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    return DocumentExtractionRecord.model_validate(payload)


def save_missing_field_answer(document_id: str, field_key: str, value: str) -> DocumentExtractionRecord:
    """Guardar una respuesta del usuario para un campo faltante y reflejar datos reutilizables."""
    normalized_field_key = field_key.strip()
    cleaned_value = ocr_clean_value(value)

    if not normalized_field_key:
        raise HTTPException(status_code=400, detail="Field key is required.")
    if normalized_field_key not in ALLOWED_MISSING_FIELD_KEYS:
        raise HTTPException(status_code=400, detail="The requested field is not supported by this MVP.")
    if not cleaned_value:
        raise HTTPException(status_code=400, detail="A non-empty answer is required.")

    record = load_extraction_record(document_id)
    record.supplemental_answers[normalized_field_key] = cleaned_value

    # Las respuestas de nivel empresa se reflejan en el perfil canonico cuando son reutilizables.
    if normalized_field_key in COMPANY_PROFILE_FIELDS:
        current_profile = load_company_profile_raw()
        current_profile[normalized_field_key] = cleaned_value
        save_company_profile(current_profile)

    save_extraction_record(record)
    return record


# ============================================================
# Funciones del perfil de empresa
# ============================================================

def company_profile_envelope(profile_data: Dict[str, Any]) -> CompanyProfileEnvelope:
    """Empaquetar el perfil en el envoltorio de respuesta de la API."""
    return CompanyProfileEnvelope(
        status="ok",
        company_profile=CompanyProfile.model_validate(profile_data),
        saved_to=str(COMPANY_PROFILE_FILE),
    )


@app.get("/company-profile", response_model=CompanyProfileEnvelope)
def get_company_profile() -> CompanyProfileEnvelope:
    """Devolver el perfil de empresa guardado actualmente."""
    return company_profile_envelope(load_company_profile())


@app.post("/company-profile/update", response_model=CompanyProfileEnvelope)
def update_company_profile(payload: CompanyProfile) -> CompanyProfileEnvelope:
    """Fusionar los valores entrantes del perfil con el perfil persistido."""
    current_profile = load_company_profile()
    incoming_data = payload.model_dump(exclude_unset=True)
    merged_profile = {**current_profile, **incoming_data}
    saved_profile = save_company_profile(merged_profile)
    return company_profile_envelope(saved_profile)


@app.post("/company-profile/import", response_model=CompanyProfileImportEnvelope)
async def import_company_profile(file: UploadFile = File(...)) -> CompanyProfileImportEnvelope:
    """Importar un JSON de perfil al almacenamiento canónico de empresa."""
    ensure_company_layout()
    ensure_company_profile_file()

    if not file.filename:
        raise HTTPException(status_code=400, detail="Se requiere un nombre de archivo JSON válido.")
    if Path(file.filename).suffix.lower() != ".json":
        raise HTTPException(status_code=400, detail="Solo se pueden importar archivos JSON como perfiles de empresa.")

    payload = decode_uploaded_json(file)
    merged_profile, imported_keys = import_company_profile_payload(payload)

    return CompanyProfileImportEnvelope(
        status="ok",
        company_profile=CompanyProfile.model_validate(merged_profile),
        saved_to=str(COMPANY_PROFILE_FILE),
        source_file_name=Path(file.filename).name,
        imported_keys=imported_keys,
        warnings=[],
    )


# ============================================================
# Carga y clasificación de archivos
# ============================================================

@app.post("/documents/upload", response_model=DocumentUploadResponse)
async def upload_document(file: UploadFile = File(...)) -> DocumentUploadResponse:
    """Guardar la carga original intacta bajo un document_id generado."""
    ensure_company_layout()
    ensure_company_profile_file()

    if not file.filename:
        raise HTTPException(status_code=400, detail="Se requiere un nombre de archivo válido.")

    document_id = build_document_id()
    original_file_name = Path(file.filename).name
    stored_file_name = build_uploaded_filename(document_id, original_file_name)
    saved_path = ORIGINALS_DIR / stored_file_name

    with saved_path.open("wb") as destination:
        shutil.copyfileobj(file.file, destination)

    return DocumentUploadResponse(
        status="ok",
        document_id=document_id,
        original_file_name=original_file_name,
        stored_file_name=stored_file_name,
        file_type=ocr_detect_file_type(original_file_name),
        saved_to=str(saved_path),
        size_bytes=saved_path.stat().st_size,
    )


# ============================================================
# Extracción de texto y OCR
# ============================================================

@app.post("/documents/{document_id}/process", response_model=DocumentExtractionRecord)
def process_document(document_id: str) -> DocumentExtractionRecord:
    """Ejecutar OCR y extracción para un documento cargado previamente."""
    ensure_company_layout()
    try:
        # El trabajo pesado de extracción vive en ocr.py; main.py solo orquesta el flujo.
        stored_file = find_uploaded_file(document_id)
        record = DocumentExtractionRecord.model_validate(
            ocr_build_extraction_record(stored_file, document_id)
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    save_extraction_record(record)
    return record


@app.get("/documents/{document_id}/extraction", response_model=DocumentExtractionRecord)
def get_document_extraction(document_id: str) -> DocumentExtractionRecord:
    """Devolver el sidecar de extracción guardado para un documento."""
    ensure_company_layout()
    try:
        return load_extraction_record(document_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


# ============================================================
# Limpieza de texto
# ============================================================

# El OCR y la limpieza de texto viven ahora en ocr.py.


# ============================================================
# Extracción por expresiones regulares
# ============================================================

# La extracción por regex también vive ahora en ocr.py.


# ============================================================
# Estado de revision y bitacora de auditoria
# ============================================================

def find_detected_item(record: DocumentExtractionRecord, item_id: str) -> Tuple[int, DetectedItem]:
    """Buscar un ítem detectado dentro de un registro de extracción por id."""
    for index, item in enumerate(record.detected_items):
        if item.item_id == item_id:
            return index, item
    raise HTTPException(status_code=404, detail=f"Detected item not found: {item_id}")


def update_reviewed_item(
    document_id: str,
    payload: ReviewItemUpdateRequest,
) -> DocumentExtractionRecord:
    """Aplicar una decisión humana de revisión a un ítem detectado."""
    record = load_extraction_record(document_id)
    item_index, detected_item = find_detected_item(record, payload.item_id)
    normalized_status = payload.status.strip().lower()

    if normalized_status not in REVIEW_STATUSES - {"pending_review"}:
        raise HTTPException(
            status_code=400,
            detail="El estado debe ser accepted, edited o discarded.",
        )

    updated_value = ocr_clean_value(payload.value) if payload.value is not None else ""
    if normalized_status == "edited" and not updated_value:
        raise HTTPException(status_code=400, detail="Los ítems editados requieren un valor no vacío.")

    if normalized_status in {"accepted", "edited"} and updated_value:
        detected_item.value = updated_value
    detected_item.status = normalized_status
    record.detected_items[item_index] = detected_item

    if payload.save_to_company_profile:
        # Solo los campos reutilizables aceptados pueden promoverse al perfil guardado.
        if normalized_status not in {"accepted", "edited"}:
            raise HTTPException(
                status_code=400,
                detail="Only accepted or edited items can be saved to the company profile.",
            )
        profile_key = COMPANY_PROFILE_REVIEW_MAP.get(detected_item.field_key)
        if not profile_key or not detected_item.reusable:
            raise HTTPException(
                status_code=400,
                detail="Only reusable company fields can be saved to the company profile.",
            )
        if not detected_item.value:
            raise HTTPException(
                status_code=400,
                detail="The selected item does not have a value to save to the company profile.",
            )
        current_profile = load_company_profile_raw()
        current_profile[profile_key] = detected_item.value
        save_company_profile(current_profile)

    save_extraction_record(record)
    return record


@app.get("/review/{document_id}", response_model=DocumentExtractionRecord)
def get_review(document_id: str) -> DocumentExtractionRecord:
    """Devolver el registro de extracción usado por la pantalla de revisión."""
    ensure_company_layout()
    try:
        return load_extraction_record(document_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/review/{document_id}/update-item", response_model=DocumentExtractionRecord)
def update_review_item(
    document_id: str,
    payload: ReviewItemUpdateRequest,
) -> DocumentExtractionRecord:
    """Actualizar el estado o el valor de un ítem revisado."""
    ensure_company_layout()
    try:
        return update_reviewed_item(document_id, payload)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/documents/{document_id}/missing-answer", response_model=DocumentExtractionRecord)
def save_document_missing_answer(
    document_id: str,
    payload: MissingFieldAnswerRequest,
) -> DocumentExtractionRecord:
    """Guardar una respuesta faltante suministrada por el usuario para un documento."""
    ensure_company_layout()
    try:
        return save_missing_field_answer(document_id, payload.field_key, payload.value)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


# ============================================================
# Deteccion de plantillas y fusion
# ============================================================

# El punto 6 agregara manejo de plantillas y logica de fusion.


# ============================================================
# Endpoints de FastAPI
# ============================================================

@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """Reportar si el MVP esta listo para servir peticiones."""
    return HealthResponse(
        status="ok",
        app_name=APP_NAME,
        version=APP_VERSION,
        checkpoint=CHECKPOINT,
        company_ready=company_layout_is_ready(),
    )


@app.get("/", response_class=HTMLResponse)
def root() -> HTMLResponse:
    """Servir el contenedor HTML del frontend."""
    return HTMLResponse(content=load_index_html())
