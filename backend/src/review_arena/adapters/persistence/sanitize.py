"""Saneado de lo que Postgres no puede almacenar.

Postgres rechaza el carácter NUL (U+0000) tanto en `text` como dentro de `jsonb`. No es
una regla de negocio sino una limitación del almacenamiento, así que se resuelve aquí, en
el adaptador, y no en el dominio. Se sustituye (no se elimina) por U+FFFD para que el
hueco sea visible al leer el contenido.
"""

from __future__ import annotations

from typing import Any, overload

_NUL = "\x00"
_REPLACEMENT = "�"


@overload
def sanitize_text(value: str) -> str: ...
@overload
def sanitize_text(value: None) -> None: ...
def sanitize_text(value: str | None) -> str | None:
    if value is None:
        return None
    return value.replace(_NUL, _REPLACEMENT)


def sanitize_json(value: Any) -> Any:
    """Sanea recursivamente cadenas (y claves) dentro de dicts y listas."""
    if isinstance(value, str):
        return sanitize_text(value)
    if isinstance(value, list):
        return [sanitize_json(item) for item in value]
    if isinstance(value, dict):
        return {sanitize_text(str(k)): sanitize_json(v) for k, v in value.items()}
    return value
