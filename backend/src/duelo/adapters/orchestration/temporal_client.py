from __future__ import annotations

import asyncio

from temporalio.client import Client


class LazyTemporalClient:
    """Conecta con Temporal en el primer uso, no al arrancar: la API debe poder levantarse
    (y responder `/health`) aunque Temporal no esté disponible. Si la conexión falla se
    reintenta en el siguiente uso."""

    def __init__(self, address: str, namespace: str = "default") -> None:
        self._address = address
        self._namespace = namespace
        self._client: Client | None = None
        self._lock = asyncio.Lock()

    async def get(self) -> Client:
        async with self._lock:
            if self._client is None:
                self._client = await Client.connect(self._address, namespace=self._namespace)
            return self._client

    async def check_health(self) -> None:
        client = await self.get()
        if not await client.service_client.check_health():
            raise ConnectionError("Temporal no está sano")
