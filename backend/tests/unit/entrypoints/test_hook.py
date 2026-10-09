"""El hook de git contra repos reales y un servidor HTTP local que hace de API."""

from __future__ import annotations

import os
import subprocess
import sys
import time
from collections.abc import Iterator
from pathlib import Path

import pytest

from duelo.adapters.git.hook_installer import FileHookInstaller
from duelo.entrypoints import hook
from tests.unit.adapters.git.helpers import Recorder, commit_file, git, init_repo

ZERO = "0" * 40


@pytest.fixture
def api() -> Iterator[Recorder]:
    recorder = Recorder()
    yield recorder
    recorder.close()


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = init_repo(tmp_path / "widgets")
    monkeypatch.chdir(path)
    return path


@pytest.fixture
def inline(monkeypatch: pytest.MonkeyPatch) -> None:
    """Sin `fork`: el trabajo se hace en el propio proceso de la prueba."""
    monkeypatch.setattr(hook, "_detach_and_run", lambda work, *, fallback_timeout: work(5.0))


def configure(monkeypatch: pytest.MonkeyPatch, api: Recorder, token: str = "tok") -> None:
    monkeypatch.setenv("INGEST_URL", api.url)
    monkeypatch.setenv("INGEST_TOKEN", token)


# --- configuración ---------------------------------------------------------------------------


def test_config_is_read_from_the_env_file(tmp_path: Path) -> None:
    env = tmp_path / "hook.env"
    env.write_text("INGEST_URL=http://x:1/\nINGEST_TOKEN = abc \n# comentario\nbasura\n")

    assert hook.load_config(env) == ("http://x:1", "abc")


def test_the_environment_wins_over_the_env_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env = tmp_path / "hook.env"
    env.write_text("INGEST_URL=http://fichero\nINGEST_TOKEN=del-fichero\n")
    monkeypatch.setenv("INGEST_TOKEN", "del-entorno")

    assert hook.load_config(env) == ("http://fichero", "del-entorno")


@pytest.mark.parametrize("content", [None, "", "INGEST_URL=http://x\n", "INGEST_TOKEN=t\n"])
def test_without_url_and_token_there_is_no_config(tmp_path: Path, content: str | None) -> None:
    env = tmp_path / "hook.env"
    if content is not None:
        env.write_text(content)

    assert hook.load_config(env) is None


def test_the_default_env_file_follows_xdg_and_falls_back_to_home(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    assert hook.default_env_path() == tmp_path / "xdg" / "duelo" / "hook.env"

    monkeypatch.delenv("XDG_CONFIG_HOME")
    monkeypatch.setenv("HOME", str(tmp_path / "casa"))
    assert hook.default_env_path() == tmp_path / "casa" / ".config" / "duelo" / "hook.env"


# --- qué se envía ----------------------------------------------------------------------------


def test_the_payload_carries_sha_title_author_branch_and_diff(repo: Path) -> None:
    sha = commit_file(repo, "x.py", "print(1)\n", "feat: título con ñ y\n\ncuerpo del mensaje")

    payload = hook.build_payload("acme/widgets", sha, "main")

    assert payload["project"] == "acme/widgets"
    assert (payload["head_sha"], payload["ref"]) == (sha, "main")
    assert (payload["title"], payload["author"]) == ("feat: título con ñ y", "Ana Pérez")
    assert "+++ b/x.py" in payload["diff"] and "+print(1)" in payload["diff"]


def test_a_huge_diff_and_long_fields_are_cut_to_what_the_api_accepts(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    sha = commit_file(repo, "x.txt", "linea\n" * 100, "t" * 800)
    monkeypatch.setattr(hook, "MAX_DIFF_CHARS", 50)

    payload = hook.build_payload("p", sha, "r" * 400)

    assert len(payload["diff"]) == 50
    assert len(payload["title"]) == hook.MAX_TITLE and len(payload["ref"]) == hook.MAX_REF


def test_the_current_branch_and_a_detached_head(repo: Path) -> None:
    sha = commit_file(repo)
    assert hook.current_branch() == "main"

    git(repo, "checkout", "-q", "--detach", sha)
    assert hook.current_branch() == "HEAD"


def test_post_sends_json_with_the_token_to_ingest_commit(api: Recorder) -> None:
    hook.post(api.url, "tok", {"project": "a/b", "head_sha": "abc"}, 5.0)

    ((path, headers, body),) = api.requests
    assert (path, body) == ("/ingest/commit", {"project": "a/b", "head_sha": "abc"})
    assert headers["X-Ingest-Token"] == "tok" and headers["Content-Type"] == "application/json"


# --- qué commits suben ------------------------------------------------------------------------


def _push_line(local: str, remote: str, branch: str = "main") -> str:
    return f"refs/heads/{branch} {local} refs/heads/{branch} {remote}\n"


def test_a_new_branch_sends_the_commits_the_remote_does_not_have(repo: Path) -> None:
    base = commit_file(repo, "a.txt", "1\n", "uno")
    git(repo, "update-ref", "refs/remotes/origin/main", base)  # el remoto ya tiene `base`
    one, two = commit_file(repo, "b.txt", "2\n", "dos"), commit_file(repo, "c.txt", "3\n", "tres")

    found = hook.pushed_commits(_push_line(two, ZERO, "feature"), "origin")

    assert found == [(one, "feature"), (two, "feature")]  # antiguos primero, sin `base`


def test_an_existing_branch_sends_the_range_remote_to_local(repo: Path) -> None:
    base = commit_file(repo, "a.txt", "1\n", "uno")
    new = commit_file(repo, "b.txt", "2\n", "dos")

    assert hook.pushed_commits(_push_line(new, base), "origin") == [(new, "main")]


def test_deletes_tags_and_malformed_lines_are_ignored(repo: Path) -> None:
    sha = commit_file(repo)
    lines = (
        f"(delete) {ZERO} refs/heads/old {sha}\n"
        f"refs/heads/main {ZERO} refs/heads/old {sha}\n"
        f"refs/tags/v1 {sha} refs/tags/v1 {ZERO}\n"
        "basura\n"
        "\n"
    )

    assert hook.pushed_commits(lines, "origin") == []


def test_at_most_twenty_commits_per_reference_are_sent(repo: Path) -> None:
    shas = [commit_file(repo, "f.txt", f"{i}\n", f"c{i}") for i in range(25)]

    found = hook.pushed_commits(_push_line(shas[-1], ZERO), "origin")

    assert len(found) == hook.MAX_PUSH_COMMITS
    assert found[-1][0] == shas[-1] and found[0][0] == shas[-20]  # los 20 más recientes


def test_a_reference_git_cannot_resolve_is_skipped_without_failing(repo: Path) -> None:
    commit_file(repo)

    assert hook.pushed_commits(_push_line("f" * 40, ZERO), "origin") == []


# --- main -------------------------------------------------------------------------------------


def test_post_commit_sends_the_new_commit(
    repo: Path, api: Recorder, inline: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    configure(monkeypatch, api, "secreto")
    sha = commit_file(repo, message="fix: algo")

    assert hook.main(["post-commit", "--project", "acme/widgets"]) == 0

    (body,) = api.wait_for(1)
    assert (body["project"], body["head_sha"], body["ref"], body["title"]) == (
        "acme/widgets",
        sha,
        "main",
        "fix: algo",
    )
    assert api.requests[0][1]["X-Ingest-Token"] == "secreto"


def test_pre_push_reads_the_refs_from_the_file_and_sends_each_commit(
    repo: Path, api: Recorder, inline: None, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    configure(monkeypatch, api)
    base = commit_file(repo, "a.txt", "1\n", "uno")
    new = commit_file(repo, "b.txt", "2\n", "dos")
    refs = tmp_path / "refs"
    refs.write_text(_push_line(new, base))

    assert (
        hook.main(["pre-push", "--project", "a/b", "--stdin-file", str(refs), "origin", "u"]) == 0
    )

    (body,) = api.wait_for(1)
    assert (body["head_sha"], body["title"]) == (new, "dos")


def test_a_failing_commit_does_not_stop_the_rest(
    repo: Path, api: Recorder, inline: None, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    configure(monkeypatch, api)
    base = commit_file(repo, "a.txt", "1\n", "uno")
    one, two = commit_file(repo, "b.txt", "2\n", "dos"), commit_file(repo, "c.txt", "3\n", "tres")
    real_post = hook.post
    calls: list[str] = []

    def flaky(url: str, token: str, payload: dict[str, str], timeout: float) -> None:
        calls.append(payload["head_sha"])
        if payload["head_sha"] == one:
            raise OSError("API caída un momento")
        real_post(url, token, payload, timeout)

    monkeypatch.setattr(hook, "post", flaky)
    refs = tmp_path / "refs"
    refs.write_text(_push_line(two, base))

    hook.main(["pre-push", "--project", "a/b", "--stdin-file", str(refs), "origin"])

    assert calls == [one, two] and [b["head_sha"] for b in api.wait_for(1)] == [two]


def test_without_configuration_nothing_is_sent_and_it_still_succeeds(
    repo: Path, api: Recorder, inline: None, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "vacio"))
    commit_file(repo)

    assert hook.main(["post-commit", "--project", "a/b"]) == 0
    time.sleep(0.2)

    assert api.requests == []


def test_a_push_with_nothing_to_send_does_not_touch_the_api(
    repo: Path, api: Recorder, inline: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    configure(monkeypatch, api)
    commit_file(repo)

    assert hook.main(["pre-push", "--project", "a/b"]) == 0  # sin --stdin-file: ninguna ref
    time.sleep(0.2)

    assert api.requests == []


@pytest.mark.parametrize("argv", [[], ["post-commit"], ["otro", "--project", "a"], ["--x"]])
def test_bad_arguments_never_fail_the_git_command(argv: list[str]) -> None:
    assert hook.main(argv) == 0


def test_outside_a_repo_it_succeeds_silently(
    tmp_path: Path, api: Recorder, inline: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    configure(monkeypatch, api)
    monkeypatch.chdir(tmp_path)

    assert hook.main(["post-commit", "--project", "a/b"]) == 0
    assert api.requests == []


# --- el proceso real: no bloquea y sale con 0 --------------------------------------------------


def run_hook(
    repo: Path, env: dict[str, str], *args: str
) -> tuple[subprocess.CompletedProcess[str], float]:
    started = time.monotonic()
    result = subprocess.run(
        [sys.executable, "-m", "duelo.entrypoints.hook", *args],
        cwd=repo,
        env={**os.environ, **env},
        capture_output=True,
        text=True,
        timeout=30,
    )
    return result, time.monotonic() - started


def test_the_real_process_returns_at_once_even_if_the_api_is_slow(repo: Path) -> None:
    slow = Recorder(delay=4.0)
    try:
        sha = commit_file(repo)

        result, elapsed = run_hook(
            repo, {"INGEST_URL": slow.url, "INGEST_TOKEN": "t"}, "post-commit", "--project", "a/b"
        )

        assert result.returncode == 0 and (result.stdout, result.stderr) == ("", "")
        assert elapsed < 3.5  # no esperó los 4 s de la respuesta
        assert slow.wait_for(1)[0]["head_sha"] == sha  # pero el envío se completó en segundo plano
    finally:
        slow.close()


@pytest.mark.parametrize("url", ["http://127.0.0.1:1", "http://no-existe.invalid"])
def test_the_real_process_exits_zero_and_quiet_when_the_api_is_down(repo: Path, url: str) -> None:
    commit_file(repo)

    result, elapsed = run_hook(
        repo, {"INGEST_URL": url, "INGEST_TOKEN": "t"}, "post-commit", "--project", "a/b"
    )

    assert (result.returncode, result.stdout, result.stderr) == (0, "", "")
    assert elapsed < 3.5


# --- de punta a punta con git y los hooks instalados --------------------------------------------


def install_hooks(repo: Path, tmp_path: Path, api: Recorder) -> None:
    import asyncio

    env_path = tmp_path / "duelo" / "hook.env"  # lo que lee el hook con XDG_CONFIG_HOME=tmp_path
    asyncio.run(
        FileHookInstaller(
            python=sys.executable, ingest_url=api.url, ingest_token="tok-e2e", env_path=env_path
        ).install(str(repo), slug="acme/widgets")
    )


def test_a_real_git_commit_reaches_the_api_and_git_does_not_wait_for_it(
    repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    slow = Recorder(delay=3.0)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    try:
        install_hooks(repo, tmp_path, slow)
        started = time.monotonic()

        sha = commit_file(repo, "app.py", "x = 1\n", "feat: desde git real")

        assert time.monotonic() - started < 2.5  # `git commit` no esperó a la API
        (body,) = slow.wait_for(1)
        assert (body["project"], body["head_sha"], body["ref"]) == ("acme/widgets", sha, "main")
        assert body["title"] == "feat: desde git real" and "+x = 1" in body["diff"]
        assert slow.requests[0][1]["X-Ingest-Token"] == "tok-e2e"
    finally:
        slow.close()


def test_a_real_git_push_sends_the_commits_made_before_the_hooks_existed(
    repo: Path, tmp_path: Path, api: Recorder, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    bare = tmp_path / "remoto.git"
    subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(bare)], check=True)
    git(repo, "remote", "add", "origin", str(bare))
    shas = [commit_file(repo, "f.txt", f"{i}\n", f"commit {i}") for i in range(3)]  # sin hooks
    install_hooks(repo, tmp_path, api)

    git(repo, "push", "-q", "origin", "main")

    sent = api.wait_for(3)
    assert [b["head_sha"] for b in sent] == shas  # los tres, más antiguos primero
    assert {b["ref"] for b in sent} == {"main"}


def test_a_commit_and_the_push_that_follows_never_break_git_with_the_api_down(
    repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    dead = Recorder()
    dead.close()
    install_hooks(repo, tmp_path, dead)
    bare = tmp_path / "remoto.git"
    subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(bare)], check=True)
    git(repo, "remote", "add", "origin", str(bare))

    commit_file(repo)  # `git commit` termina bien
    git(repo, "push", "-q", "origin", "main")  # y `git push` también

    assert git(bare, "rev-parse", "main").strip() == git(repo, "rev-parse", "HEAD").strip()
