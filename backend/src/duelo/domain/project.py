from __future__ import annotations

import re
from dataclasses import dataclass
from uuid import UUID

# Cada segmento de un slug: letras, cifras, punto, guion y guion bajo (como en GitHub), sin `.`
# ni `..` sueltos.
_SEGMENT = re.compile(r"^[A-Za-z0-9._-]+$")
_GITHUB_REMOTE = re.compile(
    r"""^(?:
        https?://(?:[^@/]+@)?github\.com/
      | ssh://(?:[^@/]+@)?github\.com(?::\d+)?/
      | (?:[^@/]+@)?github\.com:
    )
    (?P<owner>[^/]+)/(?P<repo>[^/]+?)(?:\.git)?/?$""",
    re.VERBOSE,
)
MAX_SLUG = 255


class InvalidSlug(ValueError):
    """No se puede derivar un slug válido (`owner/repo` o nombre de carpeta) de un repo."""


@dataclass(frozen=True)
class Project:
    id: UUID
    slug: str
    # Carpeta local desde la que se dio de alta; `None` si el proyecto se creó sin carpeta.
    path: str | None = None
    hooks_installed: bool = False
    github: bool = False


def _valid_segment(segment: str) -> bool:
    return segment not in {".", ".."} and _SEGMENT.fullmatch(segment) is not None


def _bounded(slug: str) -> str:
    if len(slug) > MAX_SLUG:
        raise InvalidSlug(f"El nombre del proyecto supera {MAX_SLUG} caracteres")
    return slug


def slug_for_repository(remote_url: str | None, folder_name: str) -> tuple[str, bool]:
    """Devuelve `(slug, github)`: `owner/repo` si `origin` apunta a GitHub, si no el nombre de la
    carpeta. Lanza `InvalidSlug` si el nombre elegido no es un slug válido."""
    if remote_url is not None:
        match = _GITHUB_REMOTE.fullmatch(remote_url.strip())
        if match is not None:
            owner, repo = match["owner"], match["repo"]
            if _valid_segment(owner) and _valid_segment(repo):
                return _bounded(f"{owner}/{repo}"), True
    if not _valid_segment(folder_name):
        raise InvalidSlug(f"No se puede usar {folder_name!r} como nombre de proyecto")
    return _bounded(folder_name), False
