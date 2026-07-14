from __future__ import annotations

import os
from typing import Optional

from business_bridge.adapters.secop_client import SocrataClient
from business_bridge.adapters.secop_flow import inspect_secop_value
from business_bridge.adapters.secop_models import DatasetMetadataInfo, InspectionResult


class SecopApp:
    """Capa de servicio ligera sobre el cliente Socrata y el flujo de inspeccion."""

    def __init__(self, client: Optional[SocrataClient] = None) -> None:
        self.client = client or SocrataClient(app_token=os.getenv("SECOP_APP_TOKEN"))

    def inspect(self, value: str) -> InspectionResult:
        """Inspeccionar una entrada del usuario contra los datasets oficiales."""

        return inspect_secop_value(self.client, value)

    def get_dataset_metadata(self, dataset_id: str) -> DatasetMetadataInfo:
        """Exponer metadatos cacheados del dataset a traves de un metodo de servicio."""

        return self.client.get_metadata(dataset_id)


secop_service = SecopApp()
