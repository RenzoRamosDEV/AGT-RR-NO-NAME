"""Construye la app de FastAPI con el caso de uso real y repositorios en memoria."""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID, uuid4

from fastapi import FastAPI

from duelo.application import queries
from duelo.application.ingest_commit import ChangeSubmission, IngestResult, ingest_commit, ingest_pr
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


def build_fake_api(
    *,
    max_diff_chars: int = 200_000,
    starter: FakeReviewStarter | None = None,
    operator_token: str | None = OPERATOR_TOKEN,
) -> FakeApi:
    settings = Settings(
        ingest_token=TOKEN, max_diff_chars=max_diff_chars, operator_token=operator_token
    )
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
        )

    async def get_change(change_id: UUID) -> ChangeDetail | None:
        return await queries.get_change_detail(
            changes, reviews, change_id, expected_agents=EXPECTED_AGENTS
        )

    async def retry(change_id: UUID) -> Change:
        return await retry_review(
            changes, reviews, starter, change_id, expected_agents=EXPECTED_AGENTS
        )

    async def agent_stats(project_slug: str | None) -> list[AgentStats]:
        return await queries.agent_stats(projects, reviews, project=project_slug)

    async def list_change_events(change_id: UUID) -> list[ChangeEvent] | None:
        return await queries.change_events(changes, FakeChangeEventRepository(event_log), change_id)

    async def get_review_raw_output(review_id: UUID) -> RawOutput | None:
        return await queries.review_raw_output(reviews, review_id)

    deps = ApiDependencies(
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
    )
    return FakeApi(
        create_app(settings, deps), changes, reviews, event_log, starter, settings, project, checks
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
