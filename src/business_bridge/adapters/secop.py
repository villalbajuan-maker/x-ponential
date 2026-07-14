"""Compatibility facade for SECOP parsing, client and inspection helpers."""

from business_bridge.adapters.secop_client import LOG, SocrataClient, SocrataError  # noqa: F401
from business_bridge.adapters.secop_constants import (  # noqa: F401
    DATASETS,
    DEFAULT_LIMIT,
    DEFAULT_TIMEOUT,
    USER_AGENT,
)
from business_bridge.adapters.secop_flow import inspect_secop_value  # noqa: F401
from business_bridge.adapters.secop_models import (  # noqa: F401
    DatasetMetadataInfo,
    DocumentInfo,
    InspectionResult,
    ParsedSecopInput,
)
from business_bridge.adapters.secop_parsing import parse_secop_input  # noqa: F401
from business_bridge.adapters.secop_render import (  # noqa: F401
    _render_html_index,
    _render_process_family_summaries,
    _render_process_summary,
    _render_simple_table,
)
from business_bridge.api.routes.secop import (  # noqa: F401
    api_download,
    api_inspect,
    api_metadata,
    router as secop_router,
)
from business_bridge.services.secop_service import SecopApp, secop_service  # noqa: F401

