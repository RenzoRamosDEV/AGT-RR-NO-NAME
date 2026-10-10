"""Tamaño máximo del cuerpo de la ingesta (ASGI puro).

FastAPI lee y decodifica todo el JSON antes de que el caso de uso trunque el diff, así que sin este
límite un cuerpo enorme se carga entero en memoria. Aquí se corta antes: por `Content-Length` sin
leer nada, o contando los bytes del flujo cuando no hay `Content-Length`.
"""

from __future__ import annotations

import json
from collections.abc import Collection

from starlette.types import ASGIApp, Message, Receive, Scope, Send

INGEST_PATHS = frozenset({"/ingest/commit", "/ingest/pr"})


class BodyLimitMiddleware:
    def __init__(
        self, app: ASGIApp, *, max_bytes: int, paths: Collection[str] = INGEST_PATHS
    ) -> None:
        self.app = app
        self._max_bytes = max_bytes
        self._paths = frozenset(paths)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope["method"] != "POST" or scope["path"] not in self._paths:
            await self.app(scope, receive, send)
            return

        declared = _content_length(scope)
        if declared is not None and declared > self._max_bytes:
            await self._reject(send)
            return

        received = 0
        too_large = False
        responded = False

        async def limited_receive() -> Message:
            nonlocal received, too_large
            if too_large:
                return {"type": "http.disconnect"}
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > self._max_bytes:
                    # No se lanza una excepción: FastAPI convertiría cualquier fallo al leer el
                    # cuerpo en un 400. Se le anuncia que el cliente se fue y se responde 413 abajo.
                    too_large = True
                    return {"type": "http.disconnect"}
            return message

        async def guarded_send(message: Message) -> None:
            nonlocal responded
            if not too_large:
                await send(message)
            elif not responded:
                responded = True
                await self._reject(send)
            # Con el límite superado se descarta cualquier otra respuesta de la aplicación.

        try:
            await self.app(scope, limited_receive, guarded_send)
        except Exception:
            if not too_large:
                raise
        if too_large and not responded:
            await self._reject(send)

    async def _reject(self, send: Send) -> None:
        # El mensaje solo lleva el límite configurado, nunca nada del cuerpo recibido.
        body = json.dumps({"detail": f"El cuerpo supera el máximo de {self._max_bytes} bytes."})
        payload = body.encode("utf-8")
        await send(
            {
                "type": "http.response.start",
                "status": 413,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"content-length", str(len(payload)).encode("ascii")),
                    # Parte del cuerpo quedó sin leer: la conexión no se reutiliza.
                    (b"connection", b"close"),
                ],
            }
        )
        await send({"type": "http.response.body", "body": payload})


def _content_length(scope: Scope) -> int | None:
    for name, value in scope["headers"]:
        if name == b"content-length":
            text = value.decode("latin-1").strip()
            return int(text) if text.isdigit() else None
    return None
