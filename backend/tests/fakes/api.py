"""Construye la app de FastAPI con el caso de uso real y repositorios en memoria."""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID, uuid4

from fastapi import FastAPI

from duelo.application import queries
from duelo.application.ingest_commit import ChangeSubmission, ingest_commit, ingest_pr
from duelo.application.read_models import ChangeCursor, ChangeDetail, ChangePage
from duelo.config import Settings
from duelo.domain.change import Change, ChangeKind
from duelo.domain.project import Project
from duelo.entrypoints.api.app import create_app
from duelo.entrypoints.api.dependencies import ApiDependencies, Check
from tests.fakes.change_repository import FakeChangeRepository
from tests.fakes.project_repository import FakeProjectRepository
from tests.fakes.review_repository import FakeReviewRepository
from tests.fakes.review_starter import FakeReviewStarter

TOKEN = "s3cr3t-token"
PROJECT_SLUG = "acme/widgets"


@dataclass
class FakeApi:
    app: FastAPI
    changes: FakeChangeRepository
    reviews: FakeReviewRepository
    starter: FakeReviewStarter
    settings: Settings
    project: Project
    checks: dict[str, Check] = field(default_factory=dict)


def build_fake_api(
    *, max_diff_chars: int = 200_000, starter: FakeReviewStarter | None = None
) -> FakeApi:
    settings = Settings(ingest_token=TOKEN, max_diff_chars=max_diff_chars)
    project = Project(id=uuid4(), slug=PROJECT_SLUG)
    changes = FakeChangeRepository()
    starter = starter or FakeReviewStarter()
    reviews = FakeReviewRepository()
    projects = FakeProjectRepository(project)
    checks: dict[str, Check] = {}

    async def ingest(submission: ChangeSubmission) -> Change:
        return await ingest_commit(
            projects, changes, starter, submission, max_diff_chars=settings.max_diff_chars
        )

    async def ingest_pull_request(submission: ChangeSubmission) -> Change:
        return await ingest_pr(
            projects, changes, starter, submission, max_diff_chars=settings.max_diff_chars
        )

    async def list_changes(
        slug: str, kind: ChangeKind | None, limit: int, after: ChangeCursor | None
    ) -> ChangePage:
        return await queries.list_changes(
            projects, changes, slug=slug, kind=kind, limit=limit, after=after
        )

    async def get_change(change_id: UUID) -> ChangeDetail | None:
        return await queries.get_change_detail(changes, reviews, change_id)

    deps = ApiDependencies(
        ingest_commit=ingest,
        ingest_pr=ingest_pull_request,
        list_projects=lambda: queries.list_projects(projects),
        list_changes=list_changes,
        get_change=get_change,
        agent_stats=lambda: queries.agent_stats(reviews),
        readiness_checks=checks,
    )
    return FakeApi(create_app(settings, deps), changes, reviews, starter, settings, project, checks)


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
