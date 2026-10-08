from __future__ import annotations

from review_arena.domain.change import Change
from review_arena.domain.review import Finding, ReviewResult


class FakeAgent:
    """Adaptador del puerto `ReviewAgent` sin red ni CLI real.

    Devuelve un `ReviewResult` fijo, o lanza un error si se configura para
    simular un fallo (usado en los tests de fallo parcial del workflow).
    """

    def __init__(
        self,
        name: str,
        *,
        should_fail: bool = False,
        failure_message: str = "fallo simulado",
    ) -> None:
        self.name = name
        self._should_fail = should_fail
        self._failure_message = failure_message

    async def review(self, change: Change) -> ReviewResult:
        if self._should_fail:
            raise RuntimeError(self._failure_message)

        return ReviewResult(
            summary=f"Revisión de {self.name} sobre {change.head_sha[:7]}",
            score=7,
            findings=(
                Finding(
                    severity="nit",
                    file="N/A",
                    line=0,
                    message="sin hallazgos reales (FakeAgent)",
                ),
            ),
        )
