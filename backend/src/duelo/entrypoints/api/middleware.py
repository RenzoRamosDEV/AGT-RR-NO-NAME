"""Identificador de petición y access log estructurado (ASGI puro, sin leer el cuerpo)."""

from __future__ import annotations

import json
import logging
import re
import sys
import time
from collections.abc import Callable
from uuid import uuid4

from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

REQUEST_ID_HEADER = "X-Request-ID"
# Solo se acepta un id entrante con este formato: así un cliente no puede colar saltos de línea
# ni texto arbitrario en los logs.
_VALID_REQUEST_ID = re.compile(r"[A-Za-z0-9._-]{8,64}")
_UNMATCHED = "<unmatched>"

access_logger = logging.getLogger("duelo.access")


def configure_access_logging() -> None:
    """Saca el access log por stdout (una línea JSON por petición). Idempotente. Se llama al
    componer la app real; en tests se captura el logger sin tocar la configuración global."""
    if access_logger.handlers:
        return
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("%(message)s"))
    access_logger.addHandler(handler)
    access_logger.setLevel(logging.INFO)
    access_logger.propagate = False


class RequestContextMiddleware:
    def __init__(self, app: ASGIApp, *, clock: Callable[[], float] = time.perf_counter) -> None:
        self.app = app
        self._clock = clock

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_id = _request_id_of(scope)
        status_code = 500  # si la app lanza antes de responder, el servidor contesta 500
        started = self._clock()

        async def send_with_request_id(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
                MutableHeaders(scope=message)[REQUEST_ID_HEADER] = request_id
            await send(message)

        try:
            await self.app(scope, receive, send_with_request_id)
        finally:
            route = scope.get("route")
            access_logger.info(
                json.dumps(
                    {
                        "request_id": request_id,
                        "method": scope["method"],
                        # Plantilla de la ruta, nunca la URL real: sin ids ni query string.
                        "path": getattr(route, "path", _UNMATCHED),
                        "status": status_code,
                        "duration_ms": round((self._clock() - started) * 1000, 1),
                    }
                )
            )


def _request_id_of(scope: Scope) -> str:
    for name, value in scope["headers"]:
        if name == b"x-request-id":
            candidate = value.decode("latin-1")
            if _VALID_REQUEST_ID.fullmatch(candidate):
                return str(candidate)
            break
    return uuid4().hex
