"""Utilidades compartidas por los tests de integración con Temporal y Postgres."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from duelo.adapters.persistence.change_repository import SqlAlchemyChangeRepository
from duelo.adapters.persistence.models import ReviewModel
from duelo.adapters.persistence.review_repository import SqlAlchemyReviewRepository
from duelo.application.ingest_change import ingest_change
from duelo.domain.change import Change, ChangeKind
from duelo.workflows.activities import ReviewActivities
from tests.integration.conftest import create_project


async def persist_change(
    session_factory: async_sessionmaker,
    head_sha: str,
    *,
    diff: str = "diff --git a/x b/x",
) -> Change:
    project_id = await create_project(session_factory)
    async with session_factory() as session:
        return await ingest_change(
            SqlAlchemyChangeRepository(session),
            project_id=project_id,
            kind=ChangeKind.COMMIT,
            ref="refs/heads/main",
            head_sha=head_sha,
            title="fix: algo",
            author="renzo",
            url="https://example.com/commit/" + head_sha,
            diff=diff,
            diff_truncated=False,
        )


async def reviews_for(session_factory: async_sessionmaker, change: Change) -> list[ReviewModel]:
    async with session_factory() as session:
        rows = await session.execute(select(ReviewModel).where(ReviewModel.change_id == change.id))
        return list(rows.scalars().all())


def make_activities(
    session_factory: async_sessionmaker,
    agents: dict[str, Any],
    review_repository: Callable[[AsyncSession], Any] = SqlAlchemyReviewRepository,
) -> ReviewActivities:
    return ReviewActivities(
        session_factory=session_factory,
        change_repository=SqlAlchemyChangeRepository,
        review_repository=review_repository,
        agents=agents,
    )
