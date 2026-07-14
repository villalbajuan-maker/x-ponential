from __future__ import annotations

import logging
import time

from fastapi import Request, Response

from business_bridge.core.audit import audit_event, log_event
from business_bridge.core.observability import generate_request_id, request_context

LOG = logging.getLogger("business_bridge.api")
REQUEST_ID_HEADER = "X-Request-ID"
OPERATION_ID_HEADER = "X-Operation-ID"


async def request_audit_middleware(request: Request, call_next) -> Response:
    """Correlacionar cada request y dejar un rastro estructurado de inicio a fin."""

    request_id = request.headers.get(REQUEST_ID_HEADER, "").strip() or generate_request_id()
    operation_id = request.headers.get(OPERATION_ID_HEADER, "").strip() or request_id
    route_path = request.url.path

    with request_context(
        request_id=request_id,
        operation_id=operation_id,
        method=request.method,
        path=route_path,
        route=route_path,
    ):
        started_at = time.perf_counter()
        audit_event(
            "request.started",
            f"{request.method} {route_path}",
            client_host=request.client.host if request.client else None,
            content_length=request.headers.get("content-length"),
            user_agent=request.headers.get("user-agent"),
        )
        try:
            response = await call_next(request)
        except Exception as exc:
            duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
            log_event(
                logging.ERROR,
                "request.failed",
                f"{request.method} {route_path}",
                duration_ms=duration_ms,
                error_type=exc.__class__.__name__,
                error_message=str(exc),
            )
            raise

        duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
        response.headers[REQUEST_ID_HEADER] = request_id
        response.headers[OPERATION_ID_HEADER] = operation_id
        log_event(
            logging.WARNING if response.status_code >= 400 else logging.INFO,
            "request.completed",
            f"{request.method} {route_path}",
            duration_ms=duration_ms,
            status_code=response.status_code,
            outcome="error" if response.status_code >= 400 else "ok",
        )
        return response
