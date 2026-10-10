"""Texto de «Current Details» del workflow hijo: una línea por agente, saneada y acotada."""

from __future__ import annotations

from duelo.workflows.dto import FindingPayload, RunReviewResult
from duelo.workflows.review_details import (
    ERROR_EXCERPT_CHARS,
    SUMMARY_EXCERPT_CHARS,
    render_details,
    severity_counts,
)


def _done(
    summary: str = "Todo correcto.",
    score: int | None = 8,
    findings: list[FindingPayload] | None = None,
    total: int | None = None,
) -> RunReviewResult:
    found = findings or []
    return RunReviewResult(
        status="completed",
        review_id="r",
        agent="x",
        summary=summary,
        score=score,
        findings=found,
        findings_total=len(found) if total is None else total,
    )


def _finding(severity: str) -> FindingPayload:
    return FindingPayload(severity, "a.py", 1, "m")


def test_before_any_agent_finishes_every_one_is_shown_as_working() -> None:
    assert render_details(["claude", "codex"], {}).splitlines() == [
        "### Revisión de los agentes",
        "",
        "- ⏳ **claude** · revisando…",
        "- ⏳ **codex** · revisando…",
    ]


def test_a_finished_agent_shows_its_score_findings_and_summary() -> None:
    text = render_details(
        ["claude", "codex"],
        {
            "claude": _done(
                "Cambio correcto.",
                7,
                [_finding("bug"), _finding("nit"), _finding("nit")],
            )
        },
    )

    assert text.splitlines()[2:] == [
        "- ✅ **claude** · completada · 7/10 · 3 hallazgos (1 bug, 2 nit) — Cambio correcto.",
        "- ⏳ **codex** · revisando…",
    ]


def test_a_single_finding_is_singular_and_no_findings_have_no_breakdown() -> None:
    one = render_details(["a"], {"a": _done(findings=[_finding("risk")])})
    none = render_details(["a"], {"a": _done(findings=[])})

    assert "1 hallazgo (1 risk)" in one
    assert "0 hallazgos —" in none and "(" not in none.splitlines()[2].split("—")[0]


def test_a_missing_score_is_left_out() -> None:
    line = render_details(["a"], {"a": _done(score=None)}).splitlines()[2]

    assert "completada · 0 hallazgos" in line and "/10" not in line


def test_unknown_severities_count_as_other_and_severities_keep_a_fixed_order() -> None:
    result = _done(
        findings=[_finding("nit"), _finding("???"), _finding("bug"), _finding("improvement")]
    )

    assert severity_counts(result) == "1 bug, 1 improvement, 1 nit, 1 other"


def test_a_capped_list_of_findings_shows_the_real_total_and_an_ellipsis() -> None:
    capped = _done(findings=[_finding("nit")] * 30, total=45)

    line = render_details(["a"], {"a": capped}).splitlines()[2]

    assert "45 hallazgos (30 nit…)" in line


def test_a_failed_agent_shows_its_reason() -> None:
    failed = RunReviewResult(status="failed", review_id="r", agent="codex", error="sin sesión")

    line = render_details(["codex"], {"codex": failed}).splitlines()[2]

    assert line == "- ❌ **codex** · fallida — sin sesión"


def test_a_failed_agent_without_detail_still_renders() -> None:
    failed = RunReviewResult(status="failed", review_id="r")

    assert render_details(["a"], {"a": failed}).splitlines()[2].endswith("sin detalle")


def test_long_texts_are_cut_to_an_excerpt_on_one_line() -> None:
    long_summary = _done("palabra " * 200)
    failed = RunReviewResult(status="failed", review_id="r", error="e" * 1000)

    done_line = render_details(["a"], {"a": long_summary}).splitlines()[2]
    failed_line = render_details(["b"], {"b": failed}).splitlines()[2]

    assert done_line.split(" — ", 1)[1].endswith("…")
    assert len(done_line.split(" — ", 1)[1]) <= SUMMARY_EXCERPT_CHARS + 1
    assert len(failed_line.split(" — ", 1)[1]) <= ERROR_EXCERPT_CHARS + 1


def test_what_an_agent_writes_cannot_format_the_page_or_inject_html() -> None:
    hostile = _done("**gigante** <img src=x onerror=alert(1)> [clic](http://evil)\n# título")
    text = render_details(["ag**ent"], {"ag**ent": hostile})

    line = text.splitlines()[2]
    assert "<img" not in text and "&lt;img" in line
    assert "\n" not in line
    assert "\\*\\*gigante\\*\\*" in line and "\\[clic\\]\\(http://evil\\)" in line
    assert "**ag\\*\\*ent**" in line


def test_a_secret_in_a_result_is_hidden_in_the_details_even_if_it_slipped_through() -> None:
    """Defensa en profundidad: aunque un resultado llegara sin redactar (p. ej. de otra versión),
    el texto que se publica como «Current Details» no deja ver la credencial."""
    leaky = _done("clave sk-abcdefghijklmnop1234 expuesta")
    failed = RunReviewResult(
        status="failed", review_id="r", error="falló con token=abc123tokenvalue"
    )

    text = render_details(["a", "b"], {"a": leaky, "b": failed})

    assert "sk-abcdefghijklmnop1234" not in text and "abc123tokenvalue" not in text
