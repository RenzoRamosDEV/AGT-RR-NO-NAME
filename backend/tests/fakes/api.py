"""Construye la app de FastAPI con el caso de uso real y repositorios en memoria."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from fastapi import FastAPI

from duelo.application import queries
from duelo.application.ingest_commit import ChangeSubmission, IngestResult, ingest_commit, ingest_pr
from duelo.application.local_projects import (
    SyncResult,
    add_local_project,
    remove_local_project,
    sync_pull_requests,
)
from duelo.application.ports import RateLimiter
from duelo.application.read_models import (
    AgentStats,
    ChangeCursor,
    ChangeDetail,
    ChangeEvent,
    ChangePage,
    RawOutput,
)
from duelo.application.retry_review import retry_review
from duelo.config import Settings
from duelo.domain.change import Change, ChangeKind
from duelo.domain.project import Project
from duelo.domain.review_status import ChangeReviewStatus
from duelo.entrypoints.api.app import create_app
from duelo.entrypoints.api.dependencies import ApiDependencies, Check
from tests.fakes.change_repository import FakeChangeRepository
from tests.fakes.event_log import FakeChangeEventRepository, FakeEventLog
from tests.fakes.local_projects import FakeGithubPrSource, FakeGitRepository, FakeHookInstaller
from tests.fakes.project_repository import FakeProjectRepository
from tests.fakes.review_repository import FakeReviewRepository
from tests.fakes.review_starter import FakeReviewStarter

TOKEN = "s3cr3t-token"
OPERATOR_TOKEN = "op3rator-t0ken-0123456789"  # gitleaks:allow (token falso de tests)
PROJECT_SLUG = "acme/widgets"
EXPECTED_AGENTS = 2


@dataclass
class FakeApi:
    app: FastAPI
    changes: FakeChangeRepository
    reviews: FakeReviewRepository
    events: FakeEventLog
    starter: FakeReviewStarter
    settings: Settings
    project: Project
    checks: dict[str, Check] = field(default_factory=dict)
    projects: FakeProjectRepository = field(default_factory=FakeProjectRepository)
    git: FakeGitRepository = field(default_factory=FakeGitRepository)
    hooks: FakeHookInstaller = field(default_factory=FakeHookInstaller)
    github: FakeGithubPrSource = field(default_factory=FakeGithubPrSource)


def build_fake_api(
    *,
    max_diff_chars: int = 200_000,
    starter: FakeReviewStarter | None = None,
    operator_token: str | None = OPERATOR_TOKEN,
    clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    stale_after_seconds: int = 1800,
    allowed_origins: list[str] | None = None,
    rate_limiter: RateLimiter | None = None,
    local_projects: bool = False,
    git: FakeGitRepository | None = None,
    hooks: FakeHookInstaller | None = None,
    github: FakeGithubPrSource | None = None,
) -> FakeApi:
    settings = Settings(
        ingest_token=TOKEN,
        max_diff_chars=max_diff_chars,
        operator_token=operator_token,
        stale_after_seconds=stale_after_seconds,
        allowed_origins=allowed_origins or [],
        local_projects_enabled=local_projects,
    )
    stale_after = timedelta(seconds=settings.stale_after_seconds)
    project = Project(id=uuid4(), slug=PROJECT_SLUG)
    event_log = FakeEventLog()
    reviews = FakeReviewRepository(event_log)
    changes = FakeChangeRepository(reviews, event_log)
    starter = starter or FakeReviewStarter()
    projects = FakeProjectRepository(project)
    checks: dict[str, Check] = {}

    async def ingest(submission: ChangeSubmission) -> IngestResult:
        return await ingest_commit(
            projects, changes, starter, submission, max_diff_chars=settings.max_diff_chars
        )

    async def ingest_pull_request(submission: ChangeSubmission) -> IngestResult:
        return await ingest_pr(
            projects, changes, starter, submission, max_diff_chars=settings.max_diff_chars
        )

    async def list_changes(
        slug: str,
        kind: ChangeKind | None,
        status: frozenset[ChangeReviewStatus] | None,
        q: str | None,
        limit: int,
        after: ChangeCursor | None,
    ) -> ChangePage:
        return await queries.list_changes(
            projects,
            changes,
            slug=slug,
            kind=kind,
            status=status,
            q=q,
            expected_agents=EXPECTED_AGENTS,
            limit=limit,
            after=after,
            now=clock(),
            stale_after=stale_after,
        )

    async def get_change(change_id: UUID) -> ChangeDetail | None:
        return await queries.get_change_detail(
            changes,
            reviews,
            change_id,
            expected_agents=EXPECTED_AGENTS,
            now=clock(),
            stale_after=stale_after,
        )

    async def retry(change_id: UUID) -> Change:
        return await retry_review(
            changes, reviews, starter, change_id, expected_agents=EXPECTED_AGENTS, now=clock()
        )

    async def agent_stats(project_slug: str | None) -> list[AgentStats]:
        return await queries.agent_stats(projects, reviews, project=project_slug)

    async def list_change_events(change_id: UUID) -> list[ChangeEvent] | None:
        return await queries.change_events(changes, FakeChangeEventRepository(event_log), change_id)

    async def get_review_raw_output(review_id: UUID) -> RawOutput | None:
        return await queries.review_raw_output(reviews, review_id)

    git = git or FakeGitRepository()
    hooks = hooks or FakeHookInstaller()
    github = github or FakeGithubPrSource()

    async def add_project(path: str) -> Project:
        return await add_local_project(git, hooks, projects, path)

    async def remove_project(slug: str) -> None:
        await remove_local_project(hooks, projects, projects, slug)

    async def sync_prs(slug: str) -> SyncResult:
        return await sync_pull_requests(projects, github, ingest_pull_request, slug)

    deps = ApiDependencies(
        add_local_project=add_project if local_projects else None,
        remove_project=remove_project if local_projects else None,
        sync_pull_requests=sync_prs if local_projects else None,
        ingest_commit=ingest,
        ingest_pr=ingest_pull_request,
        list_projects=lambda: queries.list_projects(projects),
        list_changes=list_changes,
        get_change=get_change,
        retry_review=retry,
        agent_stats=agent_stats,
        list_change_events=list_change_events,
        get_review_raw_output=get_review_raw_output,
        readiness_checks=checks,
        rate_limiter=rate_limiter,
    )
    return FakeApi(
        create_app(settings, deps),
        changes,
        reviews,
        event_log,
        starter,
        settings,
        project,
        checks,
        projects,
        git,
        hooks,
        github,
    )


def valid_body(**overrides: object) -> dict[str, object]:
    body: dict[str, object] = {
        "project": PROJECT_SLUG,
        "ref": "refs/heads/main",
        "head_sha": "a" * 40,
        "title": "fix: algo",
        "author": "renzo",
        "url": "https://example.com/commit/" + "a" * 40,
        "diff": "diff --git a/x b/x",
    }
    body.update(overrides)
    return body
