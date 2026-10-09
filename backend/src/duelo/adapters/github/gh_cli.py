from __future__ import annotations

import json
from dataclasses import replace

from duelo.adapters.subprocess_runner import CommandNotFound, CommandTimeout, run_command
from duelo.application.ports import GithubUnavailable, PullRequestInfo

MAX_PRS = 30
MAX_DIFF_CHARS = 1_000_000
_FIELDS = "number,title,author,headRefName,headRefOid,url,updatedAt"


class GhPrSource:
    """PRs abiertas con la CLI `gh` (ya autenticada por el usuario)."""

    def __init__(self, *, timeout: float = 30.0) -> None:
        self._timeout = timeout

    async def open_prs(self, root: str) -> list[PullRequestInfo]:
        listing = await self._gh(
            ["pr", "list", "--state", "open", "--limit", str(MAX_PRS), "--json", _FIELDS], root
        )
        try:
            raw = json.loads(listing)
        except json.JSONDecodeError as exc:
            raise GithubUnavailable("gh devolvió una respuesta que no es JSON") from exc
        if not isinstance(raw, list):
            raise GithubUnavailable("gh devolvió una respuesta inesperada")
        pulls: list[PullRequestInfo] = []
        for entry in raw:
            parsed = _parse(entry)
            if parsed is None:
                continue  # una PR malformada no debe tirar las demás
            diff = await self._gh(["pr", "diff", str(parsed.number)], root)
            pulls.append(replace(parsed, diff=diff[:MAX_DIFF_CHARS]))
        return pulls

    async def _gh(self, args: list[str], root: str) -> str:
        try:
            result = await run_command(["gh", *args], cwd=root, timeout=self._timeout)
        except CommandNotFound as exc:
            raise GithubUnavailable("gh no está instalado") from exc
        except CommandTimeout as exc:
            raise GithubUnavailable("gh no respondió a tiempo") from exc
        if result.returncode != 0:
            message = result.stderr.lower()
            if "auth" in message or "login" in message:
                raise GithubUnavailable("gh no ha iniciado sesión: ejecuta `gh auth login`")
            raise GithubUnavailable("gh no pudo consultar las PRs de este repo")
        return result.stdout


def _parse(entry: object) -> PullRequestInfo | None:
    """Una PR de `gh` (sin diff todavía), o `None` si le faltan campos o son de otro tipo."""
    if not isinstance(entry, dict):
        return None
    number, title = entry.get("number"), entry.get("title")
    ref, sha, url = entry.get("headRefName"), entry.get("headRefOid"), entry.get("url")
    author = entry.get("author")
    login = author.get("login") if isinstance(author, dict) else None
    if not isinstance(number, int) or isinstance(number, bool):
        return None
    if not (isinstance(title, str) and isinstance(ref, str) and isinstance(sha, str)):
        return None
    if not (isinstance(url, str) and ref and sha and url):
        return None
    return PullRequestInfo(
        number=number,
        title=title,
        author=login if isinstance(login, str) else "",
        ref=ref,
        head_sha=sha,
        url=url,
        diff="",
    )
