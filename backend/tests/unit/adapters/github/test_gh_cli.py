from __future__ import annotations

import json
import stat
from pathlib import Path

import pytest

from duelo.adapters.github import gh_cli
from duelo.adapters.github.gh_cli import GhPrSource
from duelo.application.ports import GithubUnavailable

LISTING = [
    {
        "number": 7,
        "title": "feat: algo",
        "author": {"login": "ana"},
        "headRefName": "feature-x",
        "headRefOid": "a" * 40,
        "url": "https://github.com/acme/widgets/pull/7",
        "updatedAt": "2026-10-10T10:00:00Z",
    },
    {
        "number": 8,
        "title": "fix: otra",
        "author": None,
        "headRefName": "fix-y",
        "headRefOid": "b" * 40,
        "url": "https://github.com/acme/widgets/pull/8",
        "updatedAt": "2026-10-10T11:00:00Z",
    },
]


def fake_gh(
    bin_dir: Path,
    listing: object = LISTING,
    *,
    exit_code: int = 0,
    stderr: str = "",
    raw_listing: str | None = None,
    sleep: float = 0,
) -> Path:
    """Un `gh` falso en el PATH: `pr list` imprime `listing`, `pr diff N` imprime un diff."""
    bin_dir.mkdir(exist_ok=True)
    listing_text = raw_listing if raw_listing is not None else json.dumps(listing)
    script = bin_dir / "gh"
    script.write_text(
        "#!/bin/sh\n"
        f"sleep {sleep}\n"
        f"echo {json.dumps(stderr)} >&2\n"
        f"[ {exit_code} -ne 0 ] && exit {exit_code}\n"
        'echo "$@" >> "$(dirname "$0")/calls"\n'
        'if [ "$2" = "list" ]; then\n'
        f"  cat <<'JSON'\n{listing_text}\nJSON\n"
        "else\n"
        '  echo "diff de la PR $3"\n'
        "fi\n"
    )
    script.chmod(script.stat().st_mode | stat.S_IEXEC)
    return script


@pytest.fixture
def bin_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "bin"
    monkeypatch.setenv("PATH", f"{path}:/usr/bin:/bin")
    return path


async def test_lists_open_prs_with_their_diff(bin_dir: Path, tmp_path: Path) -> None:
    fake_gh(bin_dir)

    pulls = await GhPrSource().open_prs(str(tmp_path))

    assert [(p.number, p.title, p.author, p.ref, p.head_sha, p.url, p.diff) for p in pulls] == [
        (7, "feat: algo", "ana", "feature-x", "a" * 40, LISTING[0]["url"], "diff de la PR 7\n"),
        (8, "fix: otra", "", "fix-y", "b" * 40, LISTING[1]["url"], "diff de la PR 8\n"),
    ]


async def test_asks_gh_for_open_prs_with_a_bounded_list(bin_dir: Path, tmp_path: Path) -> None:
    fake_gh(bin_dir)

    await GhPrSource().open_prs(str(tmp_path))

    first_call = (bin_dir / "calls").read_text().splitlines()[0]
    assert first_call == (
        f"pr list --state open --limit {gh_cli.MAX_PRS} --json "
        "number,title,author,headRefName,headRefOid,url,updatedAt"
    )


async def test_malformed_entries_are_skipped_without_losing_the_good_ones(
    bin_dir: Path, tmp_path: Path
) -> None:
    good = LISTING[0]
    broken = [
        "no-es-un-objeto",
        {**good, "number": "7"},
        {**good, "number": True},
        {**good, "title": None},
        {**good, "headRefOid": ""},
        {**good, "headRefName": 5},
        {**good, "url": ""},
    ]
    fake_gh(bin_dir, [*broken, good])

    pulls = await GhPrSource().open_prs(str(tmp_path))

    assert [p.number for p in pulls] == [7]


async def test_a_huge_diff_is_cut(
    bin_dir: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_gh(bin_dir, [LISTING[0]])
    monkeypatch.setattr(gh_cli, "MAX_DIFF_CHARS", 5)

    (pull,) = await GhPrSource().open_prs(str(tmp_path))

    assert pull.diff == "diff "


async def test_gh_not_installed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PATH", str(tmp_path / "vacio"))

    with pytest.raises(GithubUnavailable, match="no está instalado"):
        await GhPrSource().open_prs(str(tmp_path))


async def test_gh_without_a_session(bin_dir: Path, tmp_path: Path) -> None:
    fake_gh(
        bin_dir, exit_code=4, stderr="To get started with GitHub CLI, please run: gh auth login"
    )

    with pytest.raises(GithubUnavailable, match="gh auth login"):
        await GhPrSource().open_prs(str(tmp_path))


async def test_any_other_gh_failure(bin_dir: Path, tmp_path: Path) -> None:
    fake_gh(bin_dir, exit_code=1, stderr="HTTP 500")

    with pytest.raises(GithubUnavailable, match="no pudo consultar"):
        await GhPrSource().open_prs(str(tmp_path))


@pytest.mark.parametrize("raw", ["esto no es json", '{"number": 1}', "42"])
async def test_an_answer_that_is_not_a_list_of_prs(bin_dir: Path, tmp_path: Path, raw: str) -> None:
    fake_gh(bin_dir, raw_listing=raw)

    with pytest.raises(GithubUnavailable):
        await GhPrSource().open_prs(str(tmp_path))


async def test_a_gh_that_hangs_is_cut_off(bin_dir: Path, tmp_path: Path) -> None:
    fake_gh(bin_dir, sleep=30)

    with pytest.raises(GithubUnavailable, match="a tiempo"):
        await GhPrSource(timeout=0.3).open_prs(str(tmp_path))
