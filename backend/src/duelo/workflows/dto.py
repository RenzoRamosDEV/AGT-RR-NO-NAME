"""Entradas/salidas serializables de workflows y activities.

Regla binding (openspec/config.yaml): por Temporal viajan IDs y valores primitivos,
nunca datos pesados como el diff - el historial de Temporal tiene un límite de 2 MB por
payload. Cada workflow y activity recibe un único argumento dataclass para poder añadir
campos sin romper ejecuciones en curso.
"""

from __future__ import annotations

from dataclasses import dataclass

from duelo.application.review_requests import ReviewCommitInput

__all__ = [
    "ReviewChangeInput",
    "ReviewCommitInput",
    "RunReviewInput",
    "RunReviewResult",
]


@dataclass
class RunReviewInput:
    change_id: str
    agent_name: str
    run: int


@dataclass
class RunReviewResult:
    status: str
    review_id: str


@dataclass
class ReviewChangeInput:
    change_id: str
    agent_names: list[str]
    run: int = 1
