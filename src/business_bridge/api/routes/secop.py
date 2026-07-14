from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import urlparse

import requests  # type: ignore[import-untyped]
from fastapi import APIRouter, HTTPException as FastAPIHTTPException
from fastapi.responses import Response

from business_bridge.adapters.secop_constants import DEFAULT_TIMEOUT, USER_AGENT
from business_bridge.adapters.secop_render import (
    _render_process_family_summaries,
    _render_process_summary,
)
from business_bridge.adapters.secop_utils import _first_non_empty, _is_allowed_download_url
from business_bridge.services.secop_service import secop_service


router = APIRouter(tags=["secop"])


@router.get("/api/inspect")
def api_inspect(value: str = "") -> dict:
    """Ruta FastAPI que devuelve todo el payload de inspeccion en JSON."""

    if not value.strip():
        raise FastAPIHTTPException(status_code=400, detail="Missing 'value' query parameter.")
    try:
        result = secop_service.inspect(value)
        payload = result.to_dict()
        payload["process_summary"] = _render_process_summary(result)
        payload["process_family_summaries"] = _render_process_family_summaries(result)
        return payload
    except Exception as exc:  # pragma: no cover - defensive server boundary
        raise FastAPIHTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/api/download")
def api_download(url: str = "", filename: str = "") -> Response:
    """Proxy de una descarga SECOP permitida de vuelta a quien la solicita."""

    if not url:
        raise FastAPIHTTPException(status_code=400, detail="Missing 'url' query parameter.")
    if not _is_allowed_download_url(url):
        raise FastAPIHTTPException(status_code=400, detail="The requested URL is not allowed.")
    try:
        response = requests.get(
            url,
            headers={"User-Agent": USER_AGENT, "Accept": "*/*"},
            timeout=DEFAULT_TIMEOUT,
            stream=True,
            allow_redirects=True,
        )
        response.raise_for_status()
        content_type = response.headers.get("Content-Type", "application/octet-stream")
        lower_content_type = content_type.lower()
        if "text/html" in lower_content_type or "application/xhtml" in lower_content_type:
            raise ValueError(
                "The SECOP URL returned HTML instead of a file. Open the official page and complete the manual step if the site asks for it."
            )
        content = response.content
        safe_name = _first_non_empty(filename, Path(urlparse(url).path).name, "secop-document")
        safe_name = re.sub(r"[^A-Za-z0-9._-]+", "_", safe_name).strip("._-") or "secop-document"
        return Response(
            content=content,
            media_type=content_type,
            headers={
                "Content-Disposition": f'attachment; filename="{safe_name}"',
                "X-File-Name": safe_name,
            },
        )
    except Exception as exc:  # pragma: no cover - defensive server boundary
        raise FastAPIHTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/api/metadata")
def api_metadata(dataset_id: str = "") -> dict:
    """Ruta FastAPI que devuelve metadatos para un dataset id."""

    if not dataset_id.strip():
        raise FastAPIHTTPException(status_code=400, detail="Missing 'dataset_id' query parameter.")
    try:
        metadata = secop_service.get_dataset_metadata(dataset_id)
        return metadata.to_dict()
    except Exception as exc:  # pragma: no cover - defensive server boundary
        raise FastAPIHTTPException(status_code=400, detail=str(exc)) from exc
