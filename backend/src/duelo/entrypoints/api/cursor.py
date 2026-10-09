"""Cursor opaco del canal: base64url de `"{created_at ISO}|{id}"`. Es un detalle del
transporte HTTP, por eso vive aquí y no en `application/`."""

from __future__ import annotations

import base64
import binascii
from datetime import datetime
from uuid import UUID

from duelo.application.read_models import ChangeCursor


class InvalidCursor(ValueError):
    pass


def encode_cursor(cursor: ChangeCursor) -> str:
    raw = f"{cursor.created_at.isoformat()}|{cursor.id}"
    return base64.urlsafe_b64encode(raw.encode()).decode().rstrip("=")


def decode_cursor(value: str) -> ChangeCursor:
    try:
        padded = value + "=" * (-len(value) % 4)
        created_at, change_id = (
            base64.b64decode(padded, altchars=b"-_", validate=True).decode().split("|")
        )
        parsed = datetime.fromisoformat(created_at)
        if parsed.tzinfo is None:
            raise ValueError("sin zona horaria")
        return ChangeCursor(created_at=parsed, id=UUID(change_id))
    except (ValueError, binascii.Error) as exc:  # incluye UnicodeDecodeError
        raise InvalidCursor("cursor inválido") from exc
