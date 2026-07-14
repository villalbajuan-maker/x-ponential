from __future__ import annotations

import re


DATASETS = {
    "secop_ii_procesos": "p6dx-8zbt",
    "secop_i_procesos_desde_2018": "f789-7hwg",
    "secop_i_procesos_hasta_2017": "qddk-cgux",
    "secop_i_archivos_desde_2019": "ps88-5e3v",
    "secop_i_archivos_hasta_2018": "8kpz-m6cc",
    "secop_ii_archivos_2022": "kgcd-kt7i",
    "secop_ii_archivos_2023": "3skv-9na7",
    "secop_ii_archivos_2024": "nbae-kzan",
    "secop_ii_archivos_desde_2025": "dmgg-8hin",
}

SODA_RESOURCE_URL = "https://www.datos.gov.co/resource/{dataset_id}.json"
SODA_METADATA_URL = "https://www.datos.gov.co/api/views/{dataset_id}.json"

SECOP_II_PROCESS_FIELDS = ("id_del_proceso", "referencia_del_proceso")
SECOP_I_PROCESS_FIELDS = ("numero_de_constancia", "numero_de_proceso", "uid")
SECOP_II_DOCUMENT_FIELDS = ("proceso", "n_mero_de_contrato")
SECOP_I_DOCUMENT_FIELDS = ("numero_de_constancia",)
SECOP_II_PROCESS_TEXT_FIELDS = (
    "nombre_del_procedimiento",
    "descripci_n_del_procedimiento",
    "entidad",
    "fase",
    "estado_del_procedimiento",
    "modalidad_de_contratacion",
)
SECOP_I_PROCESS_TEXT_FIELDS = (
    "objeto_del_contrato_a_la",
    "detalle_del_objeto_a_contratar",
    "objeto_a_contratar",
    "nombre_entidad",
    "numero_de_proceso",
    "numero_de_constancia",
    "uid",
    "estado_del_proceso",
)
SECOP_II_DOCUMENT_TEXT_FIELDS = (
    "nombre_archivo",
    "descripci_n",
    "entidad",
    "proceso",
    "n_mero_de_contrato",
)
SECOP_I_DOCUMENT_TEXT_FIELDS = (
    "titulo",
    "descripcion",
    "nombrearchivo",
    "numero_de_constancia",
    "palabras_clave",
)

SECOP_II_DOMAINS = ("community.secop.gov.co", "www.secop.gov.co", "secop.gov.co")
SECOP_I_DOMAINS = (
    "contratos.gov.co",
    "www.contratos.gov.co",
    "www.colombiacompra.gov.co",
    "colombiacompra.gov.co",
)
SECOP_DOWNLOAD_HOSTS = SECOP_II_DOMAINS + SECOP_I_DOMAINS + ("20.96.127.85",)

SECOP_II_ID_RE = re.compile(r"^CO1\.[A-Z0-9]+(?:\.[A-Z0-9]+)+$", re.IGNORECASE)
SECOP_II_NOTICE_RE = re.compile(r"CO1\.NTC\.\d+", re.IGNORECASE)
SECOP_I_CONSTANCIA_RE = re.compile(r"^\d{2}-\d{2}-\d{6,8}$")
SECOP_GENERIC_REFERENCE_RE = re.compile(r"^[A-Z0-9][A-Z0-9\s./_-]{2,}$", re.IGNORECASE)

RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}
DEFAULT_TIMEOUT = (10, 30)
DEFAULT_LIMIT = 25
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8009
USER_AGENT = "BusinessBridge-SECOP-Script/0.1 (+local; requests)"
SEARCH_MAX_TOKENS = 14
SEARCH_MIN_TOKEN_LENGTH = 4
