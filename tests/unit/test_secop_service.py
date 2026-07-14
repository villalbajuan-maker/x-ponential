from __future__ import annotations

from types import SimpleNamespace

from business_bridge.adapters.secop_models import DatasetMetadataInfo
from business_bridge.services.secop_service import SecopApp


def test_secop_app_delegates_to_client_and_factory(monkeypatch) -> None:
    metadata = DatasetMetadataInfo(
        dataset_id="dataset-1",
        dataset_name="Dataset 1",
        queried_at="2026-07-12T12:00:00+00:00",
        last_update="2026-07-12T12:00:00+00:00",
        last_update_source="rowsUpdatedAt",
    )
    fake_client = SimpleNamespace(get_metadata=lambda dataset_id: metadata)
    inspect_calls: list[tuple[object, str]] = []

    def fake_inspect(client, value):
        inspect_calls.append((client, value))
        return {"value": value}

    monkeypatch.setattr(
        "business_bridge.services.secop_service.SocrataClient",
        lambda app_token=None: fake_client,
    )
    monkeypatch.setattr(
        "business_bridge.services.secop_service.inspect_secop_value",
        fake_inspect,
    )

    app = SecopApp()

    assert app.client is fake_client
    assert app.inspect("CO1.NTC.1234567") == {"value": "CO1.NTC.1234567"}
    assert inspect_calls == [(fake_client, "CO1.NTC.1234567")]
    assert app.get_dataset_metadata("dataset-1") == metadata
