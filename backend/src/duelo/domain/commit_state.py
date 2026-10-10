"""Estado de un commit (activo, deshecho o revertido) y las reglas puras para decidirlo.

Un commit está **deshecho** cuando su SHA ya no es alcanzable desde ninguna referencia del
repositorio local (`git reset`, `git commit --amend`, un `rebase`, borrar la rama) y **revertido**
cuando otro commit lo invierte con `git revert`. Aquí no hay git ni base de datos: solo los
criterios, para poder probarlos con conjuntos y fechas."""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from duelo.domain.change import ChangeKind


class CommitState(StrEnum):
    ACTIVE = "active"
    DISCARDED = "discarded"
    REVERTED = "reverted"


def commit_state_of(
    *, kind: ChangeKind, discarded_at: datetime | None, reverted: bool
) -> CommitState:
    """Estado de un change. Solo los commits pueden estar deshechos o revertidos (una PR siempre es
    `active`) y «deshecho» gana a «revertido»: un commit que ya no está en la rama no sigue en ella
    «revertido».

    `reverted` es verdadero si existe un commit de revert que sigue en la rama (no deshecho) y
    apunta a este: un revert que se deshace (`reset`, `amend`) deja de revertir."""
    if kind is not ChangeKind.COMMIT:
        return CommitState.ACTIVE
    if discarded_at is not None:
        return CommitState.DISCARDED
    if reverted:
        return CommitState.REVERTED
    return CommitState.ACTIVE


# Lo que escribe `git revert`: título `Revert "<título>"` (o `Reapply "<título>"` al revertir un
# revert) y, en el cuerpo, una línea EXACTA `This reverts commit <sha>.` (al revertir una fusión
# añade `, reversing` y `changes made to <sha>.` en la línea siguiente). El SHA, completo y en
# minúsculas (40 caracteres en SHA-1, 64 en SHA-256). Cualquier otra mención no cuenta.
_TITLE = re.compile(r'(?:Revert|Reapply) ".')
_REVERTS = re.compile(
    r"^This reverts commit ([0-9a-f]{40}|[0-9a-f]{64})"
    r"(?:\.|, reversing\nchanges made to (?:[0-9a-f]{40}|[0-9a-f]{64})\.)$",
    re.MULTILINE,
)


def parse_reverted_sha(title: str, body: str) -> str | None:
    """SHA que revierte un commit según su mensaje, o `None`.

    Solo el formato que genera `git revert`: título que empieza por `Revert "` o `Reapply "` y una
    línea exacta `This reverts commit <sha>.` en el cuerpo. Es lo que DECLARA el mensaje: no se
    comprueba que el parche del commit sea de verdad el inverso del original."""
    if _TITLE.match(title) is None:
        return None
    found = _REVERTS.search(body.replace("\r\n", "\n"))
    return found.group(1) if found is not None else None


# Un SHA solo puede llegar a un argumento de git si es hexadecimal: los guardados vienen de la
# ingesta y pueden ser cualquier texto (nunca deben poder ser una opción de git).
_SHA_ARGUMENT = re.compile(r"[0-9a-fA-F]{7,64}")


def is_safe_sha_argument(sha: str) -> bool:
    return _SHA_ARGUMENT.fullmatch(sha) is not None


@dataclass(frozen=True, slots=True)
class TrackedCommit:
    """Un change de tipo `commit` tal como lo ve el barrido de alcanzabilidad."""

    id: UUID
    head_sha: str
    created_at: datetime
    discarded: bool


@dataclass(frozen=True, slots=True)
class Reachability:
    """Los commits alcanzables de un repositorio, tal como los devolvió git.

    `truncated` es verdadero si git devolvió tantos commits como el máximo pedido: entonces hay
    commits alcanzables que no están en `shas`, y `oldest_at` es la fecha del más antiguo de los que
    sí están."""

    shas: frozenset[str]
    truncated: bool
    oldest_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class ReachabilityDecision:
    """Qué hacer con los commits rastreados de un proyecto tras consultar a git."""

    # Candidatos a «deshecho». Con el conjunto truncado hay que confirmarlos uno a uno antes de
    # marcarlos (`confirm_individually`).
    discard: tuple[TrackedCommit, ...]
    # Deshechos que vuelven a ser alcanzables.
    restore: tuple[TrackedCommit, ...]
    confirm_individually: bool


def normalize_sha(sha: str) -> str:
    return sha.strip().lower()


def decide_reachability(
    tracked: Iterable[TrackedCommit], reachability: Reachability
) -> ReachabilityDecision:
    """Decide qué commits pasan a «deshecho» y cuáles se recuperan.

    - Con el conjunto **completo**, que un SHA no esté en él es concluyente.
    - Con el conjunto **truncado** solo se evalúan para «deshecho» los changes creados desde la
      fecha del commit más antiguo de la ventana: un commit más antiguo puede ser alcanzable
      aunque no aparezca. Quitar la marca solo exige que el SHA esté en el conjunto.
    """
    discard: list[TrackedCommit] = []
    restore: list[TrackedCommit] = []
    for commit in tracked:
        reachable = normalize_sha(commit.head_sha) in reachability.shas
        if commit.discarded:
            if reachable:
                restore.append(commit)
            continue
        if reachable:
            continue
        if reachability.truncated and (
            reachability.oldest_at is None or commit.created_at < reachability.oldest_at
        ):
            continue
        discard.append(commit)
    return ReachabilityDecision(
        discard=tuple(discard),
        restore=tuple(restore),
        confirm_individually=reachability.truncated,
    )
