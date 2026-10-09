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
