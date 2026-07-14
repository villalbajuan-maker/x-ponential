from __future__ import annotations

from typing import Any

import pytest
import requests  # type: ignore[import-untyped]

from business_bridge.adapters.secop_client import SocrataClient, SocrataError


class FakeResponse:
    def __init__(
        self,
        status_code: int,
        json_data: Any = None,
        *,
        text: str = "",
        headers: dict[str, str] | None = None,
        json_error: bool = False,
    ) -> None:
        self.status_code = status_code
        self._json_data = json_data
        self.text = text
        self.headers = headers or {}
        self._json_error = json_error

    def json(self) -> Any:
        if self._json_error:
            raise ValueError("invalid json")
        return self._json_data


class FakeSession:
    def __init__(self, responses: list[Any]) -> None:
        self.responses = list(responses)
        self.calls: list[dict[str, Any]] = []
        self.headers: dict[str, str] = {}

    def get(self, url: str, params: dict[str, Any] | None = None, timeout: Any = None) -> Any:
        self.calls.append({"url": url, "params": params, "timeout": timeout})
        if not self.responses:
            raise AssertionError("No more fake responses configured")
        next_response = self.responses.pop(0)
        if isinstance(next_response, Exception):
            raise next_response
        return next_response


def test_request_json_retries_on_request_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    session = FakeSession(
        [
            requests.RequestException("boom"),
            FakeResponse(200, {"ok": True}),
        ]
    )
    client = SocrataClient(session=session, max_retries=1, backoff_factor=0.1)
    sleep_calls: list[float] = []

    monkeypatch.setattr("business_bridge.adapters.secop_client.random.uniform", lambda a, b: 0.0)
    monkeypatch.setattr("business_bridge.adapters.secop_client.time.sleep", lambda value: sleep_calls.append(value))

    payload = client._request_json("https://example.test", params={"page": 1})

    assert payload == {"ok": True}
    assert len(session.calls) == 2
    assert sleep_calls == [0.1]


def test_request_json_raises_on_invalid_json() -> None:
    session = FakeSession([FakeResponse(200, json_error=True)])
    client = SocrataClient(session=session, max_retries=0)

    with pytest.raises(SocrataError, match="Invalid JSON"):
        client._request_json("https://example.test")


def test_request_json_raises_on_non_retryable_status() -> None:
    session = FakeSession([FakeResponse(404, text="not found")])
    client = SocrataClient(session=session, max_retries=0)

    with pytest.raises(SocrataError, match="404"):
        client._request_json("https://example.test")


def test_get_metadata_caches_and_formats_values() -> None:
    payload = {
        "name": "Procesos SECOP",
        "columns": [{"fieldName": "a"}, {"fieldName": ""}, {"fieldName": "b"}],
        "rowsUpdatedAt": 1_700_000_000,
        "viewLastModified": 0,
        "publicationDate": 1_699_000_000,
        "createdAt": 0,
    }
    session = FakeSession([FakeResponse(200, payload)])
    client = SocrataClient(session=session)

    first = client.get_metadata("abcd-1234")
    second = client.get_metadata("abcd-1234")

    assert first is second
    assert len(session.calls) == 1
    assert session.calls[0]["url"].endswith("/abcd-1234.json")
    assert first.dataset_name == "Procesos SECOP"
    assert first.columns == ["a", "b"]
    assert first.last_update_source == "rowsUpdatedAt"
    assert first.source_url.endswith("/abcd-1234.json")


def test_query_rows_builds_parameters_and_rejects_non_list_payload() -> None:
    session = FakeSession([FakeResponse(200, [{"id": 1}]), FakeResponse(200, {"id": 2})])
    client = SocrataClient(session=session)

    rows = client.query_rows(
        "dataset-id",
        where="status = 'open'",
        select="id",
        order="id DESC",
        limit=10,
        offset=5,
        extra_params={"$q": "search"},
    )

    assert rows == [{"id": 1}]
    assert session.calls[0]["params"] == {
        "$limit": 10,
        "$offset": 5,
        "$where": "status = 'open'",
        "$select": "id",
        "$order": "id DESC",
        "$q": "search",
    }

    with pytest.raises(SocrataError, match="Unexpected response type"):
        client.query_rows("dataset-id")


def test_iter_rows_paginates_and_respects_max_rows(monkeypatch: pytest.MonkeyPatch) -> None:
    client = SocrataClient(session=FakeSession([]))
    calls: list[dict[str, Any]] = []
    pages = [
        [{"id": 1}, {"id": 2}],
        [{"id": 3}],
        [],
    ]

    def fake_query_rows(*, dataset_id: str, where=None, select=None, order=None, limit=None, offset=None):
        calls.append(
            {
                "dataset_id": dataset_id,
                "where": where,
                "select": select,
                "order": order,
                "limit": limit,
                "offset": offset,
            }
        )
        return pages.pop(0)

    monkeypatch.setattr(client, "query_rows", fake_query_rows)

    rows = list(client.iter_rows("dataset-id", page_size=2, max_rows=3))

    assert rows == [{"id": 1}, {"id": 2}, {"id": 3}]
    assert calls[0]["offset"] == 0
    assert calls[1]["offset"] == 2


def test_query_exact_any_escapes_quotes_and_logs_failures(monkeypatch: pytest.MonkeyPatch) -> None:
    client = SocrataClient(session=FakeSession([]))
    recorded_where: list[str] = []
    logged_events: list[dict[str, Any]] = []

    def fake_query_rows(*, dataset_id: str, where=None, limit=None, **kwargs):
        recorded_where.append(where)
        return [{"id": 1}]

    monkeypatch.setattr(client, "query_rows", fake_query_rows)
    monkeypatch.setattr("business_bridge.adapters.secop_client.log_event", lambda *args, **kwargs: logged_events.append({"args": args, "kwargs": kwargs}))

    rows = client.query_exact_any("dataset-id", ["field"], ["O'Brien", "O'Brien", ""], limit=5)

    assert rows == [{"id": 1}]
    assert recorded_where == ["field = 'O''Brien'"]
    assert client.query_exact_first("dataset-id", ["field"], ["O'Brien"]) == {"id": 1}
    assert client.query_exact_any("dataset-id", ["field"], []) == []

    def raise_query_rows(*args, **kwargs):
        raise SocrataError("boom")

    monkeypatch.setattr(client, "query_rows", raise_query_rows)

    assert client.query_exact_any("dataset-id", ["field"], ["value"]) == []
    assert logged_events
