"""Alta y baja de proyectos locales contra Postgres real: restricciones únicas y cascada."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker

from duelo.adapters.persistence.change_repository import SqlAlchemyChangeRepository
from duelo.adapters.persistence.models import ChangeModel, EventModel, ProjectModel, ReviewModel
from duelo.adapters.persistence.project_repository import SqlAlchemyProjectRepository
from duelo.adapters.persistence.review_repository import SqlAlchemyReviewRepository
from duelo.application.ports import ProjectAlreadyExists
from duelo.domain.change import Change, ChangeKind
from duelo.domain.events import ChangeCreated, ReviewCompleted
from duelo.domain.project import Project
from duelo.domain.review import Review, ReviewResult
from tests.integration.conftest import create_project


def _local(slug: str, path: str, *, github: bool = True) -> Project:
    return Project(id=uuid4(), slug=slug, path=path, hooks_installed=True, github=github)


async def _count(session_factory: async_sessionmaker, model: type, project_id: UUID) -> int:
    column = ChangeModel.project_id if model is ChangeModel else model.project_id  # type: ignore[attr-defined]
    async with session_factory() as session:
        return (
            await session.execute(
                select(func.count()).select_from(model).where(column == project_id)
            )
        ).scalar_one()


async def test_a_local_project_round_trips_with_all_its_fields(
    session_factory: async_sessionmaker,
) -> None:
    repo = SqlAlchemyProjectRepository(session_factory)
    slug = f"acme/{uuid4()}"

    saved = await repo.add_local(_local(slug, f"/home/u/{slug}"))

    assert await repo.get_by_slug(slug) == saved
    assert (saved.path, saved.hooks_installed, saved.github) == (f"/home/u/{slug}", True, True)
    assert saved in await repo.list_all() and saved in await repo.list_local()


async def test_a_project_without_folder_has_empty_defaults_and_is_not_local(
    session_factory: async_sessionmaker,
) -> None:
    project_id = await create_project(session_factory)
    repo = SqlAlchemyProjectRepository(session_factory)

    plain = await repo.get_by_slug(f"test-{project_id}")

    assert plain == Project(id=project_id, slug=f"test-{project_id}")
    assert plain not in await repo.list_local()


async def test_a_repeated_slug_or_folder_is_a_conflict_and_changes_nothing(
    session_factory: async_sessionmaker,
) -> None:
    repo = SqlAlchemyProjectRepository(session_factory)
    tag = uuid4()
    first = await repo.add_local(_local(f"dup/{tag}", f"/p/{tag}"))

    with pytest.raises(ProjectAlreadyExists):
        await repo.add_local(_local(f"dup/{tag}", f"/otra/{tag}"))  # mismo slug
    with pytest.raises(ProjectAlreadyExists):
        await repo.add_local(_local(f"otro/{tag}", f"/p/{tag}"))  # misma carpeta

    assert await repo.get_by_slug(f"dup/{tag}") == first
    assert await repo.get_by_slug(f"otro/{tag}") is None
    # la sesión no queda rota tras el conflicto: se puede seguir usando
    await repo.add_local(_local(f"ok/{tag}", f"/q/{tag}"))


async def test_concurrent_adds_of_the_same_folder_create_exactly_one_project(
    session_factory: async_sessionmaker,
) -> None:
    repo = SqlAlchemyProjectRepository(session_factory)
    tag = uuid4()

    results = await asyncio.gather(
        *[repo.add_local(_local(f"race{i}/{tag}", f"/misma/{tag}")) for i in range(6)],
        return_exceptions=True,
    )

    assert sum(isinstance(r, Project) for r in results) == 1
    assert sum(isinstance(r, ProjectAlreadyExists) for r in results) == 5


async def test_list_local_is_sorted_by_slug_and_skips_projects_without_folder(
    session_factory: async_sessionmaker,
) -> None:
    repo = SqlAlchemyProjectRepository(session_factory)
    tag = uuid4()
    for slug in (f"b/{tag}", f"a/{tag}"):
        await repo.add_local(_local(slug, f"/p/{slug}"))
    await create_project(session_factory)

    mine = [p.slug for p in await repo.list_local() if p.slug.endswith(str(tag))]

    assert mine == [f"a/{tag}", f"b/{tag}"]
    assert all(p.path is not None for p in await repo.list_local())


async def test_removing_a_project_deletes_its_changes_reviews_and_events_only(
    session_factory: async_sessionmaker,
) -> None:
    repo = SqlAlchemyProjectRepository(session_factory)
    tag = uuid4()
    doomed = await repo.add_local(_local(f"gone/{tag}", f"/p/gone/{tag}"))
    kept = await repo.add_local(_local(f"kept/{tag}", f"/p/kept/{tag}"))
    for project in (doomed, kept):
        change = Change.new(
            project_id=project.id,
            kind=ChangeKind.COMMIT,
            ref="main",
            head_sha="a" * 40,
            title="t",
            author="a",
            url="",
            diff="d",
            diff_truncated=False,
            created_at=datetime.now(UTC),
        )
        async with session_factory() as session:
            await SqlAlchemyChangeRepository(session).add(
                change,
                ChangeCreated(
                    change_id=change.id,
                    project_id=project.id,
                    kind="commit",
                    head_sha=change.head_sha,
                ),
            )
        review = Review.succeeded(
            change_id=change.id,
            agent="agent_1",
            run=1,
            result=ReviewResult(summary="s", score=5, findings=()),
            raw_output=None,
            duration_ms=10,
            created_at=datetime.now(UTC),
        )
        async with session_factory() as session:
            await SqlAlchemyReviewRepository(session).add(
                review,
                ReviewCompleted(
                    review_id=review.id,
                    change_id=change.id,
                    project_id=project.id,
                    agent="agent_1",
                ),
            )

    removed = await repo.remove(doomed.slug)

    assert removed == doomed
    assert await repo.get_by_slug(doomed.slug) is None
    for model in (ChangeModel, EventModel):
        assert await _count(session_factory, model, doomed.id) == 0
        assert await _count(session_factory, model, kept.id) >= 1
    async with session_factory() as session:
        orphans = (
            await session.execute(
                select(func.count())
                .select_from(ReviewModel)
                .join(ChangeModel, ReviewModel.change_id == ChangeModel.id, isouter=True)
                .where(ChangeModel.id.is_(None))
            )
        ).scalar_one()
        survivors = (
            await session.execute(
                select(func.count())
                .select_from(ReviewModel)
                .join(ChangeModel)
                .where(ChangeModel.project_id == kept.id)
            )
        ).scalar_one()
    assert orphans == 0 and survivors == 1


async def test_removing_an_unknown_or_nul_slug_returns_none(
    session_factory: async_sessionmaker,
) -> None:
    repo = SqlAlchemyProjectRepository(session_factory)

    assert await repo.remove("no/existe") is None
    assert await repo.remove("a\x00b") is None


async def test_the_unique_constraint_on_path_allows_many_projects_without_folder(
    session_factory: async_sessionmaker,
) -> None:
    for _ in range(3):
        await create_project(session_factory)  # todos con path NULL: NULL no choca consigo mismo

    async with session_factory() as session:
        nulls = (
            await session.execute(
                select(func.count()).select_from(ProjectModel).where(ProjectModel.path.is_(None))
            )
        ).scalar_one()
    assert nulls >= 3


async def test_path_of_returns_the_folder_of_a_local_project_and_none_otherwise(
    session_factory: async_sessionmaker,
) -> None:
    """`ProjectPaths`: lo que usan los agentes de CLI para leer el repositorio del proyecto."""
    repo = SqlAlchemyProjectRepository(session_factory)
    slug = f"acme/{uuid4()}"
    local = await repo.add_local(_local(slug, f"/home/u/{slug}"))
    without_folder = await create_project(session_factory)

    assert await repo.path_of(local.id) == f"/home/u/{slug}"
    assert await repo.path_of(without_folder) is None  # existe, pero sin carpeta
    assert await repo.path_of(uuid4()) is None  # no existe
