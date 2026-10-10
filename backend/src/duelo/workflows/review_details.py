"""Texto que `ReviewChangeWorkflow` publica como «Current Details» en la interfaz de Temporal.

Función pura de los resultados que ya tiene el workflow (no lee nada más), así que es determinista
en el replay. Una línea por agente: nombre, estado, nota, hallazgos por severidad y un extracto del
resumen. Todo lo que escribe un agente pasa por `escape_markdown` y se acota."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Final

from duelo.application.workflow_naming import escape_markdown, one_line
from duelo.workflows.dto import RunReviewResult

SUMMARY_EXCERPT_CHARS: Final = 200
ERROR_EXCERPT_CHARS: Final = 160
SEVERITIES: Final = ("bug", "risk", "improvement", "nit")


def severity_counts(result: RunReviewResult) -> str:
    """«1 bug, 2 nit»; las severidades desconocidas cuentan como `other`. Vacío sin hallazgos."""
    counts: dict[str, int] = {}
    for finding in result.findings:
        key = finding.severity if finding.severity in SEVERITIES else "other"
        counts[key] = counts.get(key, 0) + 1
    # `findings` puede estar recortado: el total real manda sobre la suma.
    parts = [f"{counts[key]} {key}" for key in (*SEVERITIES, "other") if key in counts]
    return ", ".join(parts)


def _agent_line(name: str, result: RunReviewResult | None) -> str:
    who = f"**{escape_markdown(one_line(name, 50))}**"
    if result is None:
        return f"- ⏳ {who} · revisando…"
    if result.status != "completed":
        reason = one_line(result.error or "sin detalle", ERROR_EXCERPT_CHARS)
        return f"- ❌ {who} · fallida — {escape_markdown(reason)}"

    score = f" · {result.score}/10" if result.score is not None else ""
    total = result.findings_total or len(result.findings)
    findings = f"{total} hallazgo{'s' if total != 1 else ''}"
    breakdown = severity_counts(result)
    if breakdown:
        findings += f" ({breakdown}{'…' if total > len(result.findings) else ''})"
    summary = one_line(result.summary or "", SUMMARY_EXCERPT_CHARS)
    tail = f" — {escape_markdown(summary)}" if summary else ""
    return f"- ✅ {who} · completada{score} · {findings}{tail}"


def render_details(
    agent_names: Sequence[str], results: Mapping[str, RunReviewResult | None]
) -> str:
    lines = ["### Revisión de los agentes", ""]
    lines.extend(_agent_line(name, results.get(name)) for name in agent_names)
    return "\n".join(lines)
