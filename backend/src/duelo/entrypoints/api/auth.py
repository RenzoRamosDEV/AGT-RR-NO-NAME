from __future__ import annotations

import hmac
from typing import Annotated

from fastapi import Header, HTTPException, Request, status


async def require_ingest_token(
    request: Request,
    x_ingest_token: Annotated[str | None, Header()] = None,
) -> None:
    expected: str = request.app.state.settings.ingest_token
    # Se compara en tiempo constante y sobre bytes (compare_digest falla con str no ASCII).
    if x_ingest_token is None or not hmac.compare_digest(
        x_ingest_token.encode(), expected.encode()
    ):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token de ingesta inválido")


async def require_operator_token(
    request: Request,
    x_operator_token: Annotated[str | None, Header()] = None,
) -> None:
    expected: str | None = request.app.state.settings.operator_token
    if expected is None:
        # Deshabilitado: 404 a toda petición, con o sin cabecera, para no delatar que existe.
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No encontrado")
    if x_operator_token is None or not hmac.compare_digest(
        x_operator_token.encode(), expected.encode()
    ):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token de operador inválido")
