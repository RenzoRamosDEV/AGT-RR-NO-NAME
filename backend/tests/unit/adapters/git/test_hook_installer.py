from __future__ import annotations

import os
import stat
import subprocess
import sys
from pathlib import Path

import pytest

from duelo.adapters.git import hook_installer
from duelo.adapters.git.hook_installer import (
    BEGIN,
    END,
    FileHookInstaller,
    insert_block,
    remove_block,
    render_block,
)
from duelo.application.ports import HookInstallError
from tests.unit.adapters.git.helpers import git, init_repo


def installer(tmp_path: Path, **overrides: object) -> FileHookInstaller:
    values: dict[str, object] = {
        "python": sys.executable,
        "ingest_url": "http://127.0.0.1:8000",
        "ingest_token": "tok-secreto",
        "env_path": tmp_path / "config" / "duelo" / "hook.env",
    }
    values.update(overrides)
    return FileHookInstaller(**values)  # type: ignore[arg-type]


def hooks_of(repo: Path) -> Path:
    return repo / ".git" / "hooks"


# --- el bloque (texto puro) ----------------------------------------------------------------


def test_the_block_goes_right_after_the_shebang_of_an_existing_hook() -> None:
    block = f"{BEGIN}\nx\n{END}"

    result = insert_block("#!/bin/bash\necho usuario\nexit 0\n", block)

    assert result == f"#!/bin/bash\n{block}\necho usuario\nexit 0\n"


def test_a_hook_without_shebang_gets_the_block_at_the_top() -> None:
    block = f"{BEGIN}\nx\n{END}"

    assert insert_block("echo usuario\n", block) == f"{block}\necho usuario\n"


def test_inserting_twice_leaves_a_single_block() -> None:
    block = f"{BEGIN}\nx\n{END}"
    once = insert_block("#!/bin/sh\necho usuario\n", block)

    assert insert_block(once, block) == once
    assert once.count(BEGIN) == 1


def test_an_updated_block_replaces_the_old_one() -> None:
    old, new = f"{BEGIN}\nviejo\n{END}", f"{BEGIN}\nnuevo\n{END}"

    result = insert_block(insert_block("#!/bin/sh\necho u\n", old), new)

    assert "viejo" not in result and "nuevo" in result


def test_removing_the_block_gives_back_the_original_text_exactly() -> None:
    original = "#!/bin/sh\n# comentario\necho usuario\n\nexit 0\n"
    block = render_block("post-commit", python="/py", slug="a/b")

    assert remove_block(insert_block(original, block)) == original


@pytest.mark.parametrize("only_ours", ["#!/bin/sh\n", "#!/bin/sh\n\n  \n", ""])
def test_a_hook_that_only_had_our_block_is_removed_entirely(only_ours: str) -> None:
    block = render_block("pre-push", python="/py", slug="a/b")

    assert remove_block(insert_block(only_ours or None, block)) is None


def test_the_block_quotes_interpreter_and_slug_so_nothing_is_interpreted(tmp_path: Path) -> None:
    """Origen: ruta y slug entran en un script de shell; con comillas simples escapadas no
    pueden ejecutar nada ni partir los argumentos."""
    marker = tmp_path / "pwned"
    fake = tmp_path / "py con 'comilla' y espacios"
    fake.write_text('#!/bin/sh\nprintf "%s\\n" "$@" > "$OUT"\n')
    fake.chmod(0o755)
    slug = f"x'; touch {marker}; echo '"
    block = render_block("post-commit", python=str(fake), slug=slug)

    subprocess.run(
        ["sh", "-c", block], check=True, env={**os.environ, "OUT": str(tmp_path / "out")}
    )

    assert not marker.exists()
    assert (tmp_path / "out").read_text().splitlines() == [
        "-m",
        "duelo.entrypoints.hook",
        "post-commit",
        "--project",
        slug,
    ]


# --- instalación en repos reales -------------------------------------------------------------


async def test_install_creates_both_hooks_executable_with_one_block_each(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "r")

    await installer(tmp_path).install(str(repo), slug="acme/widgets")

    for name in ("post-commit", "pre-push"):
        hook = hooks_of(repo) / name
        text = hook.read_text()
        assert text.startswith("#!/bin/sh\n") and text.count(BEGIN) == 1
        assert f"-m duelo.entrypoints.hook {name} --project 'acme/widgets'" in text
        assert hook.stat().st_mode & stat.S_IXUSR


async def test_install_is_idempotent(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "r")
    target = installer(tmp_path)
    await target.install(str(repo), slug="acme/widgets")
    first = {n: (hooks_of(repo) / n).read_bytes() for n in ("post-commit", "pre-push")}

    await target.install(str(repo), slug="acme/widgets")

    assert {n: (hooks_of(repo) / n).read_bytes() for n in first} == first


async def test_an_existing_user_hook_keeps_working_and_is_restored_on_uninstall(
    tmp_path: Path,
) -> None:
    repo = init_repo(tmp_path / "r")
    original = (
        '#!/bin/sh\n# del usuario\necho "hecho" > "$(git rev-parse --show-toplevel)/usuario.txt"\n'
    )
    hook = hooks_of(repo) / "post-commit"
    hook.write_text(original)
    hook.chmod(0o750)
    target = installer(tmp_path)

    await target.install(str(repo), slug="acme/widgets")
    git(repo, "commit", "-q", "--allow-empty", "-m", "x")

    assert (repo / "usuario.txt").read_text() == "hecho\n"  # su hook sigue ejecutándose
    assert hook.read_text().count(BEGIN) == 1 and original.splitlines()[1] in hook.read_text()
    assert stat.S_IMODE(hook.stat().st_mode) == 0o751  # conserva sus permisos (y sigue ejecutable)

    await target.uninstall(str(repo))

    assert hook.read_text() == original
    assert not (hooks_of(repo) / "pre-push").exists()  # el que creó Duelo desaparece


async def test_a_hook_in_another_language_is_refused_and_nothing_is_written(
    tmp_path: Path,
) -> None:
    repo = init_repo(tmp_path / "r")
    python_hook = hooks_of(repo) / "pre-push"
    python_hook.write_text("#!/usr/bin/env python3\nprint('hola')\n")

    with pytest.raises(HookInstallError, match="no es un script de shell"):
        await installer(tmp_path).install(str(repo), slug="a/b")

    assert python_hook.read_text() == "#!/usr/bin/env python3\nprint('hola')\n"
    assert not (hooks_of(repo) / "post-commit").exists()
    assert not (tmp_path / "config").exists()  # ni siquiera el hook.env


async def test_a_symlinked_hook_is_refused(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "r")
    shared = tmp_path / "compartido.sh"
    shared.write_text("#!/bin/sh\n")
    os.symlink(shared, hooks_of(repo) / "post-commit")

    with pytest.raises(HookInstallError, match="enlace simbólico"):
        await installer(tmp_path).install(str(repo), slug="a/b")

    assert shared.read_text() == "#!/bin/sh\n"


async def test_an_unreadable_hook_aborts_before_writing_anything(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "r")
    (hooks_of(repo) / "pre-push").mkdir()  # no se puede leer como fichero

    with pytest.raises(HookInstallError, match="No se puede leer"):
        await installer(tmp_path).install(str(repo), slug="a/b")

    assert not (hooks_of(repo) / "post-commit").exists()


async def test_core_hookspath_inside_the_repo_is_respected(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "r")
    git(repo, "config", "core.hooksPath", ".githooks")

    await installer(tmp_path).install(str(repo), slug="a/b")

    assert (repo / ".githooks" / "post-commit").exists()
    assert not (hooks_of(repo) / "post-commit").exists()


async def test_core_hookspath_outside_the_repo_is_refused(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "r")
    shared = tmp_path / "hooks-compartidos"
    shared.mkdir()
    git(repo, "config", "core.hooksPath", str(shared))

    with pytest.raises(HookInstallError, match="core.hooksPath apunta fuera"):
        await installer(tmp_path).install(str(repo), slug="a/b")

    assert list(shared.iterdir()) == []


async def test_a_linked_worktree_uses_the_hooks_of_the_main_repository(tmp_path: Path) -> None:
    main = init_repo(tmp_path / "main")
    git(main, "commit", "-q", "--allow-empty", "-m", "base")
    git(main, "worktree", "add", "-q", str(tmp_path / "wt"), "-b", "otra")

    await installer(tmp_path).install(str(tmp_path / "wt"), slug="a/b")

    assert (hooks_of(main) / "post-commit").exists()


async def test_the_env_file_is_private_and_holds_url_and_token(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "r")
    env_path = tmp_path / "config" / "duelo" / "hook.env"

    await installer(tmp_path, env_path=env_path).install(str(repo), slug="a/b")

    assert env_path.read_text() == "INGEST_URL=http://127.0.0.1:8000\nINGEST_TOKEN=tok-secreto\n"
    assert stat.S_IMODE(env_path.stat().st_mode) == 0o600
    assert stat.S_IMODE(env_path.parent.stat().st_mode) == 0o700
    assert "tok-secreto" not in (hooks_of(repo) / "post-commit").read_text()  # nunca en el repo


async def test_an_existing_env_file_with_loose_permissions_is_tightened(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "r")
    env_path = tmp_path / "hook.env"
    env_path.write_text("viejo")
    env_path.chmod(0o644)

    await installer(tmp_path, env_path=env_path).install(str(repo), slug="a/b")

    assert stat.S_IMODE(env_path.stat().st_mode) == 0o600


@pytest.mark.parametrize("token", ["a\nINGEST_URL=http://evil", "a\rb"])
async def test_a_token_with_line_breaks_cannot_inject_env_lines(tmp_path: Path, token: str) -> None:
    repo = init_repo(tmp_path / "r")

    with pytest.raises(HookInstallError, match="saltos de línea"):
        await installer(tmp_path, ingest_token=token).install(str(repo), slug="a/b")

    assert not (hooks_of(repo) / "post-commit").exists()


async def test_not_a_repo_is_reported(tmp_path: Path) -> None:
    (tmp_path / "suelta").mkdir()

    with pytest.raises(HookInstallError, match="No se pudo localizar"):
        await installer(tmp_path).install(str(tmp_path / "suelta"), slug="a/b")


async def test_uninstall_of_a_folder_that_no_longer_exists_does_nothing(tmp_path: Path) -> None:
    await installer(tmp_path).uninstall(str(tmp_path / "borrada"))


async def test_uninstall_leaves_alone_hooks_without_our_block(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "r")
    hook = hooks_of(repo) / "post-commit"
    hook.write_text("#!/bin/sh\necho mio\n")

    await installer(tmp_path).uninstall(str(repo))

    assert hook.read_text() == "#!/bin/sh\necho mio\n"


async def test_uninstall_in_something_that_is_not_a_repo_is_silent(tmp_path: Path) -> None:
    (tmp_path / "suelta").mkdir()

    await installer(tmp_path).uninstall(str(tmp_path / "suelta"))


# --- pre-push: stdin para los hooks posteriores ----------------------------------------------


async def test_the_pre_push_block_gives_git_s_refs_to_the_module_and_to_later_hooks(
    tmp_path: Path,
) -> None:
    repo = init_repo(tmp_path / "r")
    fake = tmp_path / "py"
    fake.write_text(
        "#!/bin/sh\n"
        'while [ "$#" -gt 0 ]; do\n'
        '  [ "$1" = "--stdin-file" ] && cat "$2" > "$OUT/modulo"\n'
        "  shift\n"
        "done\n"
    )
    fake.chmod(0o755)
    hook = hooks_of(repo) / "pre-push"
    hook.write_text('#!/bin/sh\ncat > "$OUT/usuario"\n')
    hook.chmod(0o755)
    out = tmp_path / "out"
    out.mkdir()
    await installer(tmp_path, python=str(fake)).install(str(repo), slug="a/b")
    refs = "refs/heads/main aaa refs/heads/main 000\n"

    subprocess.run(
        [str(hook), "origin", "https://example.com/r.git"],
        input=refs,
        text=True,
        check=True,
        env={**os.environ, "OUT": str(out)},
    )

    assert (out / "modulo").read_text() == refs
    assert (out / "usuario").read_text() == refs  # el hook del usuario sigue viendo stdin


# --- fallos a mitad de la escritura y entornos sin git -----------------------------------------


async def test_when_the_second_hook_cannot_be_written_the_first_goes_back_to_how_it_was(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = init_repo(tmp_path / "r")
    original = "#!/bin/sh\necho usuario\n"
    (hooks_of(repo) / "post-commit").write_text(original)
    real_write, calls = hook_installer._write_hook, 0

    def flaky(path: Path, content: str) -> None:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("disco lleno")
        real_write(path, content)

    monkeypatch.setattr(hook_installer, "_write_hook", flaky)

    with pytest.raises(HookInstallError, match="No se pudieron escribir"):
        await installer(tmp_path).install(str(repo), slug="a/b")

    assert (hooks_of(repo) / "post-commit").read_text() == original
    assert not (hooks_of(repo) / "pre-push").exists()


async def test_a_hook_created_by_this_install_is_removed_when_a_later_write_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = init_repo(tmp_path / "r")
    real_write, calls = hook_installer._write_hook, 0

    def flaky(path: Path, content: str) -> None:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("disco lleno")
        real_write(path, content)

    monkeypatch.setattr(hook_installer, "_write_hook", flaky)

    with pytest.raises(HookInstallError):
        await installer(tmp_path).install(str(repo), slug="a/b")

    assert not (hooks_of(repo) / "post-commit").exists()


async def test_a_failure_while_rolling_back_does_not_hide_the_original_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = init_repo(tmp_path / "r")
    (hooks_of(repo) / "post-commit").write_text("#!/bin/sh\n")
    real_write, calls = hook_installer._write_hook, 0

    def flaky(path: Path, content: str) -> None:
        nonlocal calls
        calls += 1
        if calls >= 2:  # falla la segunda escritura y también la restauración
            raise OSError("disco lleno")
        real_write(path, content)

    monkeypatch.setattr(hook_installer, "_write_hook", flaky)

    with pytest.raises(HookInstallError, match="No se pudieron escribir"):
        await installer(tmp_path).install(str(repo), slug="a/b")


def test_a_failed_write_leaves_no_temporary_file_behind(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def boom(*_: object) -> None:
        raise OSError("no se puede renombrar")

    monkeypatch.setattr(hook_installer.os, "replace", boom)

    with pytest.raises(OSError, match="renombrar"):
        hook_installer._write_hook(tmp_path / "post-commit", "#!/bin/sh\n")

    assert list(tmp_path.iterdir()) == []


async def test_uninstall_skips_a_hook_it_cannot_read(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "r")
    binary = hooks_of(repo) / "post-commit"
    binary.write_bytes(b"\xff\xfe# >>> duelo >>>\x00")

    await installer(tmp_path).uninstall(str(repo))

    assert binary.read_bytes() == b"\xff\xfe# >>> duelo >>>\x00"


async def test_install_without_git_in_the_path_is_reported(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = init_repo(tmp_path / "r")
    monkeypatch.setenv("PATH", str(tmp_path / "vacio"))

    with pytest.raises(HookInstallError, match="git no está disponible"):
        await installer(tmp_path).install(str(repo), slug="a/b")
