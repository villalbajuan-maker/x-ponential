from __future__ import annotations

from business_bridge.core.audit import audit_event
from business_bridge.core.observability import request_context


def test_audit_event_returns_structured_payload() -> None:
    with request_context(
        request_id="req_123",
        operation_id="op_456",
        method="POST",
        path="/documents/doc_123/process",
    ):
        event = audit_event(
            "document.processed",
            "doc_123",
            saved_to="/tmp/extraction.json",
            detected_items=4,
        )

    assert event["action"] == "document.processed"
    assert event["subject"] == "doc_123"
    assert event["details"]["saved_to"] == "/tmp/extraction.json"
    assert event["details"]["detected_items"] == 4
    assert "timestamp" in event
    assert event["schema_version"] == 1
    assert event["request_id"] == "req_123"
    assert event["operation_id"] == "op_456"
    assert event["method"] == "POST"
    assert event["path"] == "/documents/doc_123/process"
