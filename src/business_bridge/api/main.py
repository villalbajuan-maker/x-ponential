from __future__ import annotations

from fastapi import FastAPI

from business_bridge.api.middleware import request_audit_middleware
from business_bridge.api.routes.company_profile import router as company_profile_router
from business_bridge.api.routes.documents import router as documents_router
from business_bridge.api.routes.health import router as health_router
from business_bridge.api.routes.root import router as root_router
from business_bridge.api.routes.review import router as review_router
from business_bridge.api.routes.secop import router as secop_router
from business_bridge.api.runtime import (  # noqa: F401
    APP_NAME,
    APP_VERSION,
    CHECKPOINT,
    lifespan,
)
from business_bridge.core.workspace import COMPANY_PROFILE_FILE, COMPANY_ROOT, ORIGINALS_DIR  # noqa: F401


app = FastAPI(title=APP_NAME, version=APP_VERSION, lifespan=lifespan)
app.middleware("http")(request_audit_middleware)
app.include_router(company_profile_router)
app.include_router(documents_router)
app.include_router(health_router)
app.include_router(review_router)
app.include_router(root_router)
app.include_router(secop_router)
