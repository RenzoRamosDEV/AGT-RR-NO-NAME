"""Nombres legibles de los workflows: forma, saneado, unicidad y compatibilidad."""

from __future__ import annotations

from uuid import UUID

import pytest

from duelo.application.workflow_naming import (
    FALLBACK_REPO,
    MAX_REPO_CHARS,
    MAX_TITLE_CHARS,
    child_workflow_id,
    escape_markdown,
    legacy_child_workflow_id,
    legacy_parent_workflow_id,
    one_line,
    parent_workflow_id,
    project_part,
    repo_part,
    sha_part,
    static_details,
    static_summary,
)

PROJECT = UUID("ab12cd34-0000-4000-8000-000000000001")
SHA = "3f2a9c1b7d4e5f60718293a4b5c6d7e8f9012345"


@pytest.mark.parametrize(
    ("slug", "expected"),
    [
        ("acme/widgets", "acme-widgets"),
        ("Acme/Widgets", "acme-widgets"),
        ("acme/my.repo_v2", "acme-my.repo_v2"),
        ("acme//wid gets!!", "acme-wid-gets"),
        ("--acme/widgets--", "acme-widgets"),
        ("ñandú/café", "and-caf"),
        ("", FALLBACK_REPO),
        ("///", FALLBACK_REPO),
        ("../..", FALLBACK_REPO),
    ],
)
def test_the_repo_becomes_an_id_safe_fragment(slug: str, expected: str) -> None:
    assert repo_part(slug) == expected


def test_a_long_repo_is_cut_without_leaving_a_dangling_separator() -> None:
    cut = repo_part("o/" + "a" * 100)
    assert len(cut) <= MAX_REPO_CHARS
    assert cut == "o-" + "a" * (MAX_REPO_CHARS - 2)

    # El corte cae justo en un separador: no queda un `-` colgando al final.
    boundary = repo_part("a" * (MAX_REPO_CHARS - 1) + "/b")
    assert boundary == "a" * (MAX_REPO_CHARS - 1)


def test_the_sha_and_the_project_are_shortened_to_hex_fragments() -> None:
    assert sha_part(SHA) == "3f2a9c1b7d4e"
    assert sha_part("ABCDEF-12 34") == "abcdef1234"
    assert project_part(PROJECT) == "ab12cd"
    assert project_part(str(PROJECT)) == "ab12cd"


@pytest.mark.parametrize(
    ("kind", "run", "expected"),
    [
        ("commit", 1, "commit-acme-widgets-3f2a9c1b7d4e-ab12cd"),
        ("pr", 1, "pr-acme-widgets-3f2a9c1b7d4e-ab12cd"),
        ("commit", 2, "commit-acme-widgets-3f2a9c1b7d4e-ab12cd-r2"),
        ("pr", 3, "pr-acme-widgets-3f2a9c1b7d4e-ab12cd-r3"),
    ],
)
def test_the_parent_id_names_the_kind_the_repo_and_the_commit(
    kind: str, run: int, expected: str
) -> None:
    assert parent_workflow_id(kind, "acme/widgets", SHA, PROJECT, run) == expected


@pytest.mark.parametrize(
    ("kind", "run", "expected"),
    [
        ("commit", 1, "review-commit-acme-widgets-3f2a9c1b7d4e-ab12cd-r1"),
        ("commit", 2, "review-commit-acme-widgets-3f2a9c1b7d4e-ab12cd-r2"),
        ("pr", 1, "review-pr-acme-widgets-3f2a9c1b7d4e-ab12cd-r1"),
    ],
)
def test_the_child_id_names_the_kind_and_always_carries_the_run(
    kind: str, run: int, expected: str
) -> None:
    assert child_workflow_id(kind, "acme/widgets", SHA, PROJECT, run) == expected


def test_a_commit_and_a_pr_with_the_same_sha_get_different_child_ids() -> None:
    """Regresión: sin el tipo en el id del hijo, el commit y la PR de un mismo proyecto con el
    mismo SHA (dos changes distintos) compartían id: el segundo hijo no arrancaba y su review no
    se hacía nunca. Lo destapó el e2e de lectura."""
    assert child_workflow_id("commit", "acme/widgets", SHA, PROJECT, 1) != child_workflow_id(
        "pr", "acme/widgets", SHA, PROJECT, 1
    )


def test_a_readded_project_with_the_same_name_gets_a_different_id() -> None:
    """Regresión: con un id solo con el nombre, quitar un proyecto y volver a añadirlo con el
    mismo nombre haría que Temporal ignorase en silencio el commit repetido (la ejecución
    anterior, ya completada, ocuparía el id)."""
    other = UUID("99ff00aa-0000-4000-8000-000000000002")

    assert parent_workflow_id("commit", "acme/widgets", SHA, PROJECT, 1) != parent_workflow_id(
        "commit", "acme/widgets", SHA, other, 1
    )
    assert child_workflow_id("commit", "acme/widgets", SHA, PROJECT, 1) != child_workflow_id(
        "commit", "acme/widgets", SHA, other, 1
    )


def test_names_that_clash_once_sanitized_still_get_different_ids() -> None:
    second = UUID("cd34ef56-0000-4000-8000-000000000003")

    assert repo_part("Acme/Widgets") == repo_part("acme/widgets")
    assert parent_workflow_id("commit", "Acme/Widgets", SHA, PROJECT, 1) != parent_workflow_id(
        "commit", "acme/widgets", SHA, second, 1
    )


def test_a_commit_and_a_pr_with_the_same_sha_do_not_clash() -> None:
    assert parent_workflow_id("commit", "acme/widgets", SHA, PROJECT, 1) != parent_workflow_id(
        "pr", "acme/widgets", SHA, PROJECT, 1
    )


def test_the_ids_are_stable_for_the_same_inputs() -> None:
    first = parent_workflow_id("commit", "acme/widgets", SHA, PROJECT, 1)
    assert first == parent_workflow_id("commit", "acme/widgets", SHA, PROJECT, 1)


def test_the_legacy_ids_keep_their_historic_shape() -> None:
    assert legacy_parent_workflow_id("commit", PROJECT, SHA, 1) == f"commit-{PROJECT}-{SHA}"
    assert legacy_parent_workflow_id("pr", PROJECT, SHA, 2) == f"pr-{PROJECT}-{SHA}-r2"
    assert legacy_child_workflow_id("abc", 1) == "review-abc-r1"
    assert legacy_child_workflow_id("abc", 4) == "review-abc-r4"


def test_one_line_flattens_whitespace_and_control_characters_and_cuts_with_an_ellipsis() -> None:
    assert one_line("hola\n\n  mundo\t\x00fin", 50) == "hola mundo fin"
    assert one_line("abcdefghij", 10) == "abcdefghij"
    assert one_line("abcdefghijk", 10) == "abcdefghi…"
    assert one_line("   ", 10) == ""


def test_the_static_summary_names_the_kind_the_repo_and_the_title() -> None:
    assert (
        static_summary("commit", "acme/widgets", "fix: algo") == "commit · acme/widgets · fix: algo"
    )
    assert static_summary("pr", "acme/widgets", "") == "pr · acme/widgets"
    assert static_summary("pr", "acme/widgets", "  \n ") == "pr · acme/widgets"

    long = static_summary("commit", "a/b", "x" * 500)
    assert len(long) == len("commit · a/b · ") + MAX_TITLE_CHARS
    assert long.endswith("…")


def test_the_static_summary_is_one_line_even_with_a_hostile_title() -> None:
    summary = static_summary("commit", "a/b", "uno\ndos\r\ntres")
    assert "\n" not in summary and "\r" not in summary
    assert summary == "commit · a/b · uno dos tres"


@pytest.mark.parametrize(
    ("raw", "escaped"),
    [
        ("texto normal", "texto normal"),
        ("**negrita**", "\\*\\*negrita\\*\\*"),
        ("`code`", "\\`code\\`"),
        ("[a](http://x)", "\\[a\\]\\(http://x\\)"),
        ("<script>alert(1)</script>", "&lt;script\\>alert\\(1\\)&lt;/script\\>"),
        ("a & b", "a &amp; b"),
        ("# título | col", "\\# título \\| col"),
    ],
)
def test_the_markdown_and_the_html_of_an_untrusted_text_have_no_effect(
    raw: str, escaped: str
) -> None:
    assert escape_markdown(raw) == escaped


def test_the_details_card_lists_what_identifies_the_workflow() -> None:
    card = static_details(
        kind="pr",
        slug="acme/widgets",
        sha=SHA,
        title="feat: *algo*",
        change_id="c-1",
        run=2,
    )

    assert card.splitlines() == [
        "**Tipo:** pr",
        "**Repositorio:** acme/widgets",
        "**SHA:** `3f2a9c1b7d4e`",
        "**Título:** feat: \\*algo\\*",
        "**Run:** 2",
        "**Change:** `c-1`",
    ]


def test_the_details_card_survives_an_empty_title() -> None:
    card = static_details(kind="commit", slug="a/b", sha="abc", title="", change_id="c", run=1)
    assert "**Título:** _(sin título)_" in card


def test_separators_at_the_edges_do_not_eat_the_length_budget() -> None:
    """Los `-`, `.` y `_` de los extremos se quitan antes de cortar a 60 caracteres, no después."""
    assert repo_part("-" + "a" * 70) == "a" * MAX_REPO_CHARS
    assert repo_part("..." + "a" * 70) == "a" * MAX_REPO_CHARS


def test_runs_of_dashes_collapse_into_one() -> None:
    assert repo_part("a--b---c") == "a-b-c"


def test_the_project_fragment_ignores_non_hex_characters_instead_of_replacing_them() -> None:
    assert project_part("ab-12-cd-ef") == "ab12cd"


def test_a_cut_text_does_not_keep_the_space_before_the_ellipsis() -> None:
    assert one_line("abcd efghij", 6) == "abcd…"


def test_the_repo_in_the_summary_and_the_card_is_cut_at_exactly_80_characters() -> None:
    exact, over = "a" * 80, "a" * 81
    cut = "a" * 79 + "…"

    assert static_summary("commit", exact, "") == f"commit · {exact}"
    assert static_summary("commit", over, "") == f"commit · {cut}"
    card = static_details(kind="commit", slug=over, sha="abc", title="t", change_id="c", run=1)
    assert f"**Repositorio:** {cut}" in card
    card = static_details(kind="commit", slug=exact, sha="abc", title="t", change_id="c", run=1)
    assert f"**Repositorio:** {exact}" in card


def test_a_backtick_in_the_change_id_cannot_close_its_code_span() -> None:
    card = static_details(kind="pr", slug="a/b", sha="abc", title="t", change_id="a`b", run=1)

    assert "**Change:** `ab`" in card


def test_a_secret_in_the_title_is_hidden_in_the_summary_and_the_card() -> None:
    """El título del change (lo escribe el autor del commit) va al historial de Temporal en el
    resumen y la ficha estáticos."""
    title = "fix: usar token=abc123tokenvalue y sk-abcdefghijklmnop1234"

    summary = static_summary("commit", "a/b", title)
    card = static_details(kind="commit", slug="a/b", sha="abc", title=title, change_id="c", run=1)

    for text in (summary, card):
        assert "abc123tokenvalue" not in text and "sk-abcdefghijklmnop1234" not in text
    assert summary == "commit · a/b · fix: usar token=[oculto] y [oculto]"
