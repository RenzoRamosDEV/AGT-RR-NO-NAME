"""Nombres de los workflows de review tal y como se ven en la interfaz de Temporal.

Funciones puras (solo `str` e `int`) porque las usan a la vez el adaptador que arranca el workflow y
el propio workflow, que no puede tocar la base de datos para calcularlos.

Formato nuevo: `{kind}-{repo}-{sha12}-{proyecto6}[-r{run}]` para el padre y
`review-{kind}-{repo}-{sha12}-{proyecto6}-r{run}` para el hijo, por ejemplo
`commit-acme-widgets-3f2a9c1b7d4e-ab12cd` y `review-commit-acme-widgets-3f2a9c1b7d4e-ab12cd-r1`.

El sufijo `proyecto6` (los 6 primeros hex del UUID del proyecto) es lo que mantiene el id único y
estable: sin él, quitar un proyecto y volver a añadirlo con el mismo nombre, o dos nombres que
saneados coinciden (`Acme/Widgets` y `acme/widgets`), harían que Temporal ignorase en silencio el
commit repetido por la política `ALLOW_DUPLICATE_FAILED_ONLY`. Lo único que podría colisionar es
que dos commits del mismo proyecto compartan los primeros 12 hex del SHA (2^-48 por pareja).
"""

from __future__ import annotations

import re
from uuid import UUID

from duelo.application.payload_limits import redact_secrets

MAX_REPO_CHARS = 60
SHA_CHARS = 12
PROJECT_CHARS = 6
MAX_TITLE_CHARS = 120
FALLBACK_REPO = "proyecto"

_NOT_ID_CHARS = re.compile(r"[^a-z0-9._-]+")
_NOT_HEX = re.compile(r"[^a-z0-9]+")
_CONTROL = re.compile(r"[\x00-\x1f\x7f-\x9f]+")


def repo_part(slug: str) -> str:
    """`owner/repo` como fragmento de id: minúsculas, solo `[a-z0-9._-]` (el resto, incluida la
    barra, pasa a `-`), sin guiones repetidos ni en los extremos y de 60 caracteres como máximo."""
    clean = _NOT_ID_CHARS.sub("-", slug.lower())
    clean = re.sub(r"-{2,}", "-", clean).strip("-._")[:MAX_REPO_CHARS].strip("-._")
    return clean or FALLBACK_REPO


def sha_part(sha: str) -> str:
    return _NOT_HEX.sub("", sha.lower())[:SHA_CHARS]


def project_part(project_id: str | UUID) -> str:
    return _NOT_HEX.sub("", str(project_id).lower())[:PROJECT_CHARS]


def _suffix(run: int) -> str:
    return "" if run == 1 else f"-r{run}"


def parent_workflow_id(kind: str, slug: str, sha: str, project_id: str | UUID, run: int) -> str:
    """Id del workflow padre (`commit-…`, `pr-…`); el del primer `run` no lleva sufijo."""
    base = f"{kind}-{repo_part(slug)}-{sha_part(sha)}-{project_part(project_id)}"
    return f"{base}{_suffix(run)}"


def child_workflow_id(kind: str, slug: str, sha: str, project_id: str | UUID, run: int) -> str:
    """Id del hijo `ReviewChangeWorkflow` (`review-{kind}-…-r{run}`); lleva siempre el `run`. El
    tipo es imprescindible: un commit y una PR del mismo proyecto con el mismo SHA son changes
    distintos y sus hijos no pueden compartir id."""
    return f"review-{kind}-{repo_part(slug)}-{sha_part(sha)}-{project_part(project_id)}-r{run}"


def legacy_parent_workflow_id(kind: str, project_id: str | UUID, sha: str, run: int) -> str:
    """Id con el formato anterior (UUID del proyecto y SHA completo): sirve para no relanzar una
    review que ya arrancó con él."""
    return f"{kind}-{project_id}-{sha}{_suffix(run)}"


def legacy_child_workflow_id(change_id: str, run: int) -> str:
    return f"review-{change_id}-r{run}"


def one_line(text: str, limit: int) -> str:
    """Texto en una sola línea, sin caracteres de control y acotado (con «…» si se corta)."""
    flat = " ".join(_CONTROL.sub(" ", text).split())
    return flat if len(flat) <= limit else f"{flat[: limit - 1].rstrip()}…"


_MARKDOWN_SPECIAL = re.compile(r"([\\`*_{}\[\]()#+!|~>-])")


def escape_markdown(text: str) -> str:
    """Texto sin efecto en el markdown (y sin HTML) que pinta la interfaz de Temporal: lo que
    escribe un agente o un autor no debe poder maquetar ni inyectar etiquetas."""
    return _MARKDOWN_SPECIAL.sub(r"\\\1", text.replace("&", "&amp;").replace("<", "&lt;"))


def safe_title(title: str) -> str:
    """Título del change listo para el historial de Temporal: una línea, acotado y sin
    credenciales (lo escribe el autor del commit y puede contener cualquier cosa)."""
    return one_line(redact_secrets(title), MAX_TITLE_CHARS)


def static_summary(kind: str, slug: str, title: str) -> str:
    """Línea que la lista de Temporal muestra junto al workflow: «commit · acme/widgets · título»"""
    parts = [kind, one_line(slug, 80)]
    clean_title = safe_title(title)
    if clean_title:
        parts.append(clean_title)
    return " · ".join(parts)


def static_details(*, kind: str, slug: str, sha: str, title: str, change_id: str, run: int) -> str:
    """Ficha en markdown del workflow (pestaña «Details» de su página en Temporal)."""
    clean_title = safe_title(title)
    shown_title = escape_markdown(clean_title) if clean_title else "_(sin título)_"
    return "\n".join(
        [
            f"**Tipo:** {escape_markdown(kind)}",
            f"**Repositorio:** {escape_markdown(one_line(slug, 80))}",
            f"**SHA:** `{sha_part(sha)}`",
            f"**Título:** {shown_title}",
            f"**Run:** {run}",
            f"**Change:** `{change_id.replace('`', '')}`",  # en un bloque de código no se escapa
        ]
    )
