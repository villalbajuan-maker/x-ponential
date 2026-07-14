from __future__ import annotations

from typing import Dict, List
from urllib.parse import urlparse

from business_bridge.adapters.secop_constants import (
    SECOP_GENERIC_REFERENCE_RE,
    SECOP_I_CONSTANCIA_RE,
    SECOP_I_DOMAINS,
    SECOP_II_DOMAINS,
    SECOP_II_ID_RE,
    SECOP_II_NOTICE_RE,
)
from business_bridge.adapters.secop_models import ParsedSecopInput
from business_bridge.adapters.secop_utils import (
    _collect_query_params,
    _is_url,
    _query_param_case_insensitive,
    _unique_preserve_order,
)


def parse_secop_input(value: str) -> ParsedSecopInput:
    """Clasificar la entrada del usuario como SECOP I, SECOP II, URL, id o referencia."""

    raw_value = (value or "").strip()
    if not raw_value:
        return ParsedSecopInput(
            raw_value="",
            input_kind="empty",
            platform="unknown",
            identifier="",
        )

    is_url = _is_url(raw_value)
    original_url = raw_value if is_url else ""
    domain = ""
    path = ""
    params: Dict[str, List[str]] = {}
    matched_parameters: List[str] = []
    identifier_candidates: List[str] = []
    identifier = raw_value
    platform = "unknown"
    input_kind = "reference"

    if is_url:
        parsed = urlparse(raw_value)
        domain = parsed.netloc.lower()
        path = parsed.path
        params = _collect_query_params(parsed.query)
        normalized_path = parsed.path.lower()

        secop_ii_domain = any(domain.endswith(item) for item in SECOP_II_DOMAINS)
        secop_i_domain = any(domain.endswith(item) for item in SECOP_I_DOMAINS)

        notice_values = _query_param_case_insensitive(
            params, "noticeUID", "processUID", "processId", "id"
        )
        constancia_values = _query_param_case_insensitive(
            params,
            "numConstancia",
            "numeroConstancia",
            "idProceso",
            "IDProceso",
        )

        if (
            secop_ii_domain
            or "public/tendering/opportunitydetail/index" in normalized_path
            or notice_values
        ):
            platform = "secop_ii"
            input_kind = "url"
            if notice_values:
                identifier_candidates.extend(notice_values)
                matched_parameters.extend(
                    [
                        name
                        for name in params
                        if name.casefold() in {"noticeuid", "processuid", "processid", "id"}
                    ]
                )
            else:
                regex_matches = SECOP_II_NOTICE_RE.findall(raw_value)
                if regex_matches:
                    identifier_candidates.extend(regex_matches)
                    matched_parameters.append("noticeUID-regex")
                else:
                    generic_matches = SECOP_II_ID_RE.findall(raw_value)
                    if generic_matches:
                        identifier_candidates.extend(generic_matches)
                        matched_parameters.append("secop-ii-id")
            if not identifier_candidates and raw_value:
                identifier_candidates.append(raw_value)

        elif secop_i_domain or constancia_values:
            platform = "secop_i"
            input_kind = "url"
            if constancia_values:
                identifier_candidates.extend(constancia_values)
                matched_parameters.extend(
                    [
                        name
                        for name in params
                        if name.casefold() in {"numconstancia", "numeroconstancia", "idproceso"}
                    ]
                )
            else:
                if SECOP_I_CONSTANCIA_RE.match(raw_value):
                    identifier_candidates.append(raw_value)
                    matched_parameters.append("constancia-directa")
            if not identifier_candidates and raw_value:
                identifier_candidates.append(raw_value)
        else:
            identifier_candidates.append(raw_value)

    else:
        if SECOP_II_ID_RE.match(raw_value) or SECOP_II_NOTICE_RE.match(raw_value):
            platform = "secop_ii"
            input_kind = "identifier"
            identifier_candidates.append(raw_value)
            matched_parameters.append("secop-ii-id")
        elif SECOP_I_CONSTANCIA_RE.match(raw_value):
            platform = "secop_i"
            input_kind = "constancia"
            identifier_candidates.append(raw_value)
            matched_parameters.append("constancia")
        elif raw_value.upper().startswith("CO1."):
            platform = "secop_ii"
            input_kind = "identifier"
            identifier_candidates.append(raw_value)
            matched_parameters.append("secop-ii-prefix")
        else:
            input_kind = "reference"
            identifier_candidates.append(raw_value)
            if SECOP_GENERIC_REFERENCE_RE.match(raw_value):
                matched_parameters.append("generic-reference")

    identifier_candidates = _unique_preserve_order(identifier_candidates)
    identifier = identifier_candidates[0] if identifier_candidates else raw_value

    return ParsedSecopInput(
        raw_value=raw_value,
        input_kind=input_kind,
        platform=platform,
        identifier=identifier,
        original_url=original_url,
        domain=domain,
        path=path,
        query_params=params,
        matched_parameters=tuple(_unique_preserve_order(matched_parameters)),
        identifier_candidates=tuple(identifier_candidates),
    )
