"""Límites y saneado de lo que se copia de una review al historial de Temporal.

Por Temporal no viaja el diff ni la salida cruda de un CLI (cada payload tiene un tope de 2 MB y el
historial se guarda entero), pero sí un extracto acotado de la respuesta del reviewer para poder
leerla en su interfaz. Todo lo que sale de aquí es un valor ya acotado: ningún campo puede crecer
sin límite aunque el agente devuelva un texto enorme."""

from __future__ import annotations

import re

MAX_SUMMARY_CHARS = 2000
MAX_FINDINGS = 30
MAX_MESSAGE_CHARS = 300
MAX_FILE_CHARS = 300
MAX_ERROR_CHARS = 300

_HIDDEN = "[oculto]"
_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]")
# El valor de `Authorization: Bearer abc` es `abc`, no `Bearer`: el esquema se consume con él.
_SECRET_PAIR = re.compile(
    r"\b(token|secret|password|passwd|api[_-]?key|authorization)(\s*[=:]\s*)"
    r"(?:(?:Bearer|Basic)\s+)?\S+",
    re.IGNORECASE,
)
_BEARER = re.compile(r"\bBearer\s+\S+", re.IGNORECASE)
_KEY_LIKE = re.compile(r"\bsk-[A-Za-z0-9_-]{8,}")


def bound(text: str, limit: int) -> tuple[str, bool]:
    """`text` sin caracteres de control (se conservan saltos de línea y tabuladores) y acotado a
    `limit` caracteres; el booleano indica si se cortó."""
    clean = _CONTROL.sub(" ", text)
    if len(clean) <= limit:
        return clean, False
    return f"{clean[: limit - 1].rstrip()}…", True


def redact_secrets(text: str) -> str:
    """Oculta lo que parece una credencial en un mensaje de error (`token=…`, `Bearer …`,
    `sk-…`). El error de un fallo puede arrastrar lo que quiera decir una excepción."""
    hidden = _SECRET_PAIR.sub(rf"\1\2{_HIDDEN}", text)
    hidden = _BEARER.sub(f"Bearer {_HIDDEN}", hidden)
    return _KEY_LIKE.sub(_HIDDEN, hidden)


def bound_error(error: str) -> tuple[str, bool]:
    """Error de una review fallida listo para el historial: sin credenciales y acotado."""
    return bound(redact_secrets(error), MAX_ERROR_CHARS)
