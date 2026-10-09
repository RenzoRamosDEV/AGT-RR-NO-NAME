"""Dobles de los puertos de proyectos locales: git, hooks y GitHub."""

from __future__ import annotations

from duelo.application.ports import (
    GithubUnavailable,
    HookInstallError,
    InvalidRepository,
    PullRequestInfo,
    RepoInfo,
)


class FakeGitRepository:
    def __init__(self, info: RepoInfo | None = None, error: str | None = None) -> None:
        self.info = info or RepoInfo(root="/home/u/widgets", remote_url=None)
        self.error = error
        self.inspected: list[str] = []

    async def inspect(self, path: str) -> RepoInfo:
        self.inspected.append(path)
        if self.error is not None:
            raise InvalidRepository(self.error)
        return self.info


class FakeHookInstaller:
    def __init__(self, *, install_error: str | None = None, uninstall_fails: bool = False) -> None:
        self.install_error = install_error
        self.uninstall_fails = uninstall_fails
        self.installed: list[tuple[str, str]] = []
        self.uninstalled: list[str] = []

    async def install(self, root: str, *, slug: str) -> None:
        if self.install_error is not None:
            raise HookInstallError(self.install_error)
        self.installed.append((root, slug))

    async def uninstall(self, root: str) -> None:
        if self.uninstall_fails:
            raise HookInstallError("no se pudo")
        self.uninstalled.append(root)


class FakeGithubPrSource:
    def __init__(
        self, prs: list[PullRequestInfo] | None = None, *, unavailable: str | None = None
    ) -> None:
        self.prs = prs or []
        self.unavailable = unavailable
        self.queried: list[str] = []

    async def open_prs(self, root: str) -> list[PullRequestInfo]:
        self.queried.append(root)
        if self.unavailable is not None:
            raise GithubUnavailable(self.unavailable)
        return list(self.prs)


def pull_request(number: int = 1, **overrides: object) -> PullRequestInfo:
    values: dict[str, object] = {
        "number": number,
        "title": f"feat: pr {number}",
        "author": "ana",
        "ref": f"feature-{number}",
        "head_sha": f"{number:040x}",
        "url": f"https://github.com/acme/widgets/pull/{number}",
        "diff": "diff --git a/x b/x\n--- a/x\n+++ b/x\n@@ -1 +1 @@\n-a\n+b\n",
    }
    values.update(overrides)
    return PullRequestInfo(**values)  # type: ignore[arg-type]
