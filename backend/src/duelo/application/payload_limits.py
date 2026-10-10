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
MAX_SEVERITY_CHARS = 40

_HIDDEN = "[oculto]"
_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]")
# El valor de `Authorization: Bearer abc` es `abc`, no `Bearer`: el esquema se consume con él.
_SECRET_PAIR = re.compile(
    r"\b(token|secret|password|passwd|api[_-]?key|authorization)(\s*[=:]\s*)"
    r"(?:(?:Bearer|Basic)\s+)?\S+",
    re.IGNORECASE,
)
_BEARER = re.compile(r"\bBearer\s+\S+", re.IGNORECASE)
# Credenciales con forma reconocible que un revisor puede citar al avisar de que están en el diff.
_KEY_LIKE = re.compile(r"\bsk-[A-Za-z0-9_-]{8,}")
_GITHUB_TOKEN = re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}")
_AWS_KEY_ID = re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")
_SLACK_TOKEN = re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}")
_JWT = re.compile(r"\beyJ[A-Za-z0-9_-]{5,}\.[A-Za-z0-9_-]{5,}\.[A-Za-z0-9_-]{5,}")
_PRIVATE_KEY = re.compile(
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?(?:-----END [A-Z ]*PRIVATE KEY-----|\Z)", re.DOTALL
)
_KEY_SHAPES = (_KEY_LIKE, _GITHUB_TOKEN, _AWS_KEY_ID, _SLACK_TOKEN, _JWT, _PRIVATE_KEY)


def bound(text: str, limit: int) -> tuple[str, bool]:
    """`text` sin caracteres de control (se conservan saltos de línea y tabuladores) y acotado a
    `limit` caracteres; el booleano indica si se cortó."""
    clean = _CONTROL.sub(" ", text)
    if len(clean) <= limit:
        return clean, False
    return f"{clean[: limit - 1].rstrip()}…", True


def redact_secrets(text: str) -> str:
    """Oculta lo que parece una credencial (`token=…`, `Authorization: Bearer …`, `sk-…`, tokens de
    GitHub, claves de AWS, tokens de Slack, JWT y claves privadas PEM).

    Vale para cualquier texto que vaya al historial de Temporal, que es inmutable: el error de un
    fallo (arrastra lo que diga una excepción), pero también el resumen y los hallazgos de una
    review completada, porque un revisor que avisa de que hay una credencial en el diff la cita."""
    hidden = _SECRET_PAIR.sub(rf"\1\2{_HIDDEN}", text)
    hidden = _BEARER.sub(f"Bearer {_HIDDEN}", hidden)
    for shape in _KEY_SHAPES:
        hidden = shape.sub(_HIDDEN, hidden)
    return hidden


def bound_redacted(text: str, limit: int) -> tuple[str, bool]:
    """`bound` de un texto ya sin credenciales. Se redacta ANTES de cortar: un `sk-…` partido por
    el límite dejaría de casar con el patrón y su principio quedaría a la vista."""
    return bound(redact_secrets(text), limit)


def bound_error(error: str) -> tuple[str, bool]:
    """Error de una review fallida listo para el historial: sin credenciales y acotado."""
    return bound_redacted(error, MAX_ERROR_CHARS)
