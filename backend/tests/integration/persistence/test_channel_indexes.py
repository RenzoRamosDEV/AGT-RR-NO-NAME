"""Índices del canal: existen, la migración es reversible y las consultas los usan de verdad.

El EXPLAIN va contra la consulta real del repositorio (no una copia) con datos suficientes para
que el planificador elija por coste, sin forzar `enable_seqscan`."""

from __future__ import annotations

import asyncio
import os
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from uuid import UUID, uuid4

from alembic import command
from alembic.config import Config
from sqlalchemy import event, inspect, text
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

from duelo.adapters.persistence.change_repository import SqlAlchemyChangeRepository
from duelo.domain.change import ChangeKind
from duelo.domain.review_status import ChangeReviewStatus

BACKEND_DIR = Path(__file__).resolve().parents[3]
PREVIOUS_REVISION = "c3f1a7d92b40"

NEW_CHANGES_INDEXES = {
    "ix_changes_project_created_at_id": ["project_id", "created_at", "id"],
    "ix_changes_project_kind_created_at_id": ["project_id", "kind", "created_at", "id"],
}
NEW_REVIEWS_INDEXES = {"ix_reviews_change_run_status": ["change_id", "run", "status"]}


def _alembic() -> Config:
    return Config(str(BACKEND_DIR / "alembic.ini"))


async def _indexes(engine: AsyncEngine, table: str) -> dict[str, list[str]]:
    async with engine.connect() as conn:
        found = await conn.run_sync(lambda c: inspect(c).get_indexes(table))
    return {i["name"]: list(i["column_names"]) for i in found if i["name"]}


async def test_the_migration_creates_the_channel_indexes_and_drops_the_ones_they_replace(
    engine: AsyncEngine,
) -> None:
    changes = await _indexes(engine, "changes")
    reviews = await _indexes(engine, "reviews")

    assert NEW_CHANGES_INDEXES.items() <= changes.items()
    assert NEW_REVIEWS_INDEXES.items() <= reviews.items()
    assert "ix_changes_project_created_at" not in changes  # sustituido por (…, created_at, id)
    assert "ix_reviews_change_id" not in reviews  # sustituido por (change_id, run, status)


async def test_downgrading_one_step_restores_the_previous_indexes_and_upgrading_redoes_them(
    database_url: str, engine: AsyncEngine
) -> None:
    os.environ["DATABASE_URL"] = database_url

    await asyncio.to_thread(command.downgrade, _alembic(), PREVIOUS_REVISION)
    changes, reviews = await _indexes(engine, "changes"), await _indexes(engine, "reviews")
    assert changes["ix_changes_project_created_at"] == ["project_id", "created_at"]
    assert reviews["ix_reviews_change_id"] == ["change_id"]
    assert not NEW_CHANGES_INDEXES.keys() & changes.keys()
    assert not NEW_REVIEWS_INDEXES.keys() & reviews.keys()

    await asyncio.to_thread(command.upgrade, _alembic(), "head")
    assert NEW_CHANGES_INDEXES.items() <= (await _indexes(engine, "changes")).items()
    assert NEW_REVIEWS_INDEXES.items() <= (await _indexes(engine, "reviews")).items()


async def _seed(engine: AsyncEngine) -> tuple[UUID, UUID]:
    """Dos proyectos con miles de changes (un tercio PR) y dos reviews por change."""
    a, b = uuid4(), uuid4()
    async with engine.begin() as conn:
        await conn.execute(
            text("INSERT INTO projects (id, slug) VALUES (:a, :sa), (:b, :sb)"),
            {"a": a, "sa": f"plan-a-{a}", "b": b, "sb": f"plan-b-{b}"},
        )
        await conn.execute(
            text(
                """
                INSERT INTO changes (id, project_id, kind, ref, head_sha, title, author, url,
                                     diff, diff_truncated, status, run, created_at)
                SELECT gen_random_uuid(),
                       CASE WHEN g % 2 = 0 THEN CAST(:a AS uuid) ELSE CAST(:b AS uuid) END,
                       CASE WHEN g % 3 = 0 THEN 'pr' ELSE 'commit' END,
                       'main', md5(g::text), 't' || g, 'u' || (g % 7), '', '', false, 'pending', 1,
                       now() - (g || ' seconds')::interval
                FROM generate_series(1, 8000) g
                """
            ),
            {"a": a, "b": b},
        )
        await conn.execute(
            text(
                """
                INSERT INTO reviews (id, change_id, agent, run, status, findings)
                SELECT gen_random_uuid(), c.id, agent, 1,
                       CASE WHEN random() < 0.3 THEN 'failed' ELSE 'completed' END, '[]'::jsonb
                FROM changes c CROSS JOIN (VALUES ('agent_1'), ('agent_2')) AS v(agent)
                """
            )
        )
    # VACUUM también deja el mapa de visibilidad al día, que permite los index-only scans.
    async with engine.connect() as conn:
        autocommit = await conn.execution_options(isolation_level="AUTOCOMMIT")
        await autocommit.execute(text("VACUUM ANALYZE"))
    return a, b


@contextmanager
def _capture_plans(engine: AsyncEngine) -> Iterator[list[str]]:
    plans: list[str] = []

    def explain(conn, cursor, statement, parameters, context, executemany):  # type: ignore[no-untyped-def]
        if statement.lstrip().upper().startswith("SELECT") and "FROM changes" in statement:
            cursor.execute("EXPLAIN " + statement, parameters)
            plans.append("\n".join(row[0] for row in cursor.fetchall()))

    event.listen(engine.sync_engine, "before_cursor_execute", explain)
    try:
        yield plans
    finally:
        event.remove(engine.sync_engine, "before_cursor_execute", explain)


async def _plan(
    engine: AsyncEngine, project: UUID, *, kind: ChangeKind | None = None, status=None
) -> str:
    sessions = async_sessionmaker(engine)
    with _capture_plans(engine) as plans:
        async with sessions() as session:
            await SqlAlchemyChangeRepository(session).list_for_project(
                project, kind=kind, status=status, q=None, expected_agents=2, limit=21, after=None
            )
    (plan,) = plans
    return plan


async def test_the_channel_query_walks_the_index_and_counts_reviews_index_only(
    engine: AsyncEngine,
) -> None:
    project, _ = await _seed(engine)

    unfiltered = await _plan(engine, project)
    by_kind = await _plan(engine, project, kind=ChangeKind.PR)
    by_status = await _plan(engine, project, status=frozenset({ChangeReviewStatus.FAILED}))

    for plan in (unfiltered, by_kind, by_status):
        # Sin ordenar todo el proyecto ni agregar todas las reviews: se recorre el índice en
        # orden inverso y se cuentan las reviews de cada change con un index-only scan.
        assert "Index Scan Backward" in plan, plan
        assert "Index Only Scan using ix_reviews_change_run_status" in plan, plan
        assert "Seq Scan" not in plan and "Sort" not in plan and "HashAggregate" not in plan, plan
    assert "ix_changes_project_created_at_id" in unfiltered
    assert "ix_changes_project_kind_created_at_id" in by_kind
    assert "ix_changes_project_created_at_id" in by_status
