"""Una PR con el mismo SHA y diff que un commit ya revisado reutiliza sus reviews y no arranca
workflow (no gasta la suscripción de los agentes)."""

from datetime import UTC, datetime
from uuid import uuid4

from duelo.application.ingest_change import ingest_change
from duelo.application.ingest_commit import (
    ChangeSubmission,
    IngestResult,
    ingest_commit,
    ingest_pr,
)
from duelo.domain.change import Change, ChangeKind
from duelo.domain.events import ChangeCreated, ReviewCompleted, ReviewReused
from duelo.domain.project import Project
from duelo.domain.review import Finding, Review, ReviewResult
from tests.fakes.change_repository import FakeChangeRepository
from tests.fakes.project_repository import FakeProjectRepository
from tests.fakes.review_repository import FakeReviewRepository
from tests.fakes.review_starter import FakeReviewStarter

PROJECT = Project(id=uuid4(), slug="acme/widgets")
AGENTS = ("claude", "codex")
SHA = "c" * 40
DIFF = "diff --git a/a.py b/a.py\n+x\n"
NOW = datetime(2026, 1, 2, tzinfo=UTC)


class World:
    def __init__(self) -> None:
        self.reviews = FakeReviewRepository()
        self.changes = FakeChangeRepository(self.reviews)
        self.projects = FakeProjectRepository(PROJECT)
        self.starter = FakeReviewStarter()

    def submission(self, **overrides: object) -> ChangeSubmission:
        values: dict[str, object] = {
            "project": PROJECT.slug,
            "ref": "main",
            "head_sha": SHA,
            "title": "feat: algo",
            "author": "renzo",
            "url": "",
            "diff": DIFF,
        }
        values.update(overrides)
        return ChangeSubmission(**values)  # type: ignore[arg-type]

    async def commit(self, **overrides: object) -> IngestResult:
        return await ingest_commit(
            self.projects,
            self.changes,
            self.starter,
            self.submission(**overrides),
            max_diff_chars=1000,
        )

    async def pr(self, *, agents: tuple[str, ...] = AGENTS, **overrides: object) -> IngestResult:
        return await ingest_pr(
            self.projects,
            self.changes,
            self.starter,
            self.submission(**overrides),
            max_diff_chars=1000,
            agent_names=agents,
        )

    async def review(self, change: Change, agent: str, *, fail: bool = False) -> None:
        if fail:
            review = Review.failed(
                change_id=change.id,
                agent=agent,
                run=1,
                error="caído",
                duration_ms=1,
                created_at=NOW,
            )
        else:
            review = Review.succeeded(
                change_id=change.id,
                agent=agent,
                run=1,
                result=ReviewResult(
                    summary=f"resumen de {agent}",
                    score=8,
                    findings=(Finding("risk", "a.py", 1, "ojo"),),
                ),
                raw_output="cruda",
                duration_ms=900,
                created_at=NOW,
            )
        await self.reviews.add(
            review,
            ReviewCompleted(
                review_id=review.id, change_id=change.id, project_id=PROJECT.id, agent=agent
            ),
        )

    async def reviewed_commit(self) -> Change:
        commit = (await self.commit()).change
        for agent in AGENTS:
            await self.review(commit, agent)
        return commit


def _started_kinds(world: World) -> set[str]:
    return {key[0] for key in world.starter.started}


async def test_a_pr_identical_to_a_reviewed_commit_is_born_reviewed_without_a_workflow() -> None:
    world = World()
    commit = await world.reviewed_commit()

    result = await world.pr()

    assert result.created and result.reused
    assert _started_kinds(world) == {"commit"}  # la PR no arrancó nada
    copies = await world.reviews.list_for_change(result.change.id)
    assert sorted(c.agent for c in copies) == ["claude", "codex"]
    for copy in copies:
        assert copy.reused_from_change_id == commit.id
        assert (copy.run, copy.summary, copy.score) == (1, f"resumen de {copy.agent}", 8)
        assert copy.raw_output is None
        assert copy.created_at == result.change.created_at  # la misma marca de tiempo del alta
    kinds = [type(e) for e in world.changes.persisted_events]
    assert kinds.count(ChangeCreated) == 2  # el del commit y el de la PR
    reused_events = [e for e in world.reviews.persisted_events if isinstance(e, ReviewReused)]
    assert sorted(e.agent for e in reused_events) == ["claude", "codex"]
    assert {e.project_id for e in reused_events} == {PROJECT.id}
    assert {e.reused_from_change_id for e in reused_events} == {commit.id}


async def test_resending_a_reused_pr_copies_and_starts_nothing() -> None:
    world = World()
    await world.reviewed_commit()
    first = await world.pr()

    again = await world.pr()

    assert again.change.id == first.change.id
    assert not again.created and again.reused
    assert _started_kinds(world) == {"commit"}
    assert len(await world.reviews.list_for_change(first.change.id)) == 2
    assert len([e for e in world.reviews.persisted_events if isinstance(e, ReviewReused)]) == 2


async def test_a_pr_with_a_different_diff_is_reviewed_normally() -> None:
    world = World()
    await world.reviewed_commit()

    result = await world.pr(diff=DIFF + "+otra cosa\n")

    assert result.created and not result.reused
    assert _started_kinds(world) == {"commit", "pr"}
    assert await world.reviews.list_for_change(result.change.id) == []


async def test_a_pr_is_reviewed_normally_when_an_agent_has_not_finished() -> None:
    world = World()
    commit = (await world.commit()).change
    await world.review(commit, "claude")  # falta codex: el commit aún se revisa

    result = await world.pr()

    assert not result.reused
    assert _started_kinds(world) == {"commit", "pr"}
    assert await world.reviews.list_for_change(result.change.id) == []


async def test_a_pr_is_reviewed_normally_when_an_agent_failed_on_the_commit() -> None:
    world = World()
    commit = (await world.commit()).change
    await world.review(commit, "claude")
    await world.review(commit, "codex", fail=True)

    result = await world.pr()

    assert not result.reused
    assert _started_kinds(world) == {"commit", "pr"}


async def test_a_pr_without_a_matching_commit_is_reviewed_normally() -> None:
    world = World()

    result = await world.pr()

    assert result.created and not result.reused
    assert _started_kinds(world) == {"pr"}


async def test_without_the_expected_agents_nothing_is_reused() -> None:
    world = World()
    await world.reviewed_commit()

    result = await world.pr(agents=())

    assert not result.reused
    assert _started_kinds(world) == {"commit", "pr"}


async def test_a_commit_never_reuses_the_reviews_of_a_pr() -> None:
    world = World()
    pr = (await world.pr()).change
    for agent in AGENTS:
        await world.review(pr, agent)

    commit = await world.commit()

    assert commit.created and not commit.reused
    assert _started_kinds(world) == {"commit", "pr"}


async def test_a_retried_pr_is_a_normal_pr_again() -> None:
    world = World()
    await world.reviewed_commit()
    reused = (await world.pr()).change
    advanced = await world.changes.advance_run(reused.id, from_run=1, started_at=NOW)
    assert advanced is not None and advanced.run == 2

    again = await world.pr()

    assert not again.reused
    assert ("pr", str(PROJECT.id), SHA, 2) in world.starter.started


class _SpyChanges(FakeChangeRepository):
    """Cuenta las búsquedas del commit hermano: solo una PR con agentes esperados debe hacerlas."""

    def __init__(self, reviews: FakeReviewRepository) -> None:
        super().__init__(reviews)
        self.lookups = 0

    async def find_commit_with_reviews(self, project_id, head_sha):  # type: ignore[no-untyped-def]
        self.lookups += 1
        return await super().find_commit_with_reviews(project_id, head_sha)


async def _lookups(kind: ChangeKind, agents: tuple[str, ...]) -> int:
    reviews = FakeReviewRepository()
    changes = _SpyChanges(reviews)
    await ingest_change(
        changes,
        project_id=PROJECT.id,
        kind=kind,
        ref="main",
        head_sha=SHA,
        title="t",
        author="a",
        url="",
        diff=DIFF,
        diff_truncated=False,
        agent_names=agents,
    )
    return changes.lookups


async def test_only_a_pr_with_expected_agents_looks_for_a_commit_to_reuse() -> None:
    assert await _lookups(ChangeKind.PR, AGENTS) == 1
    assert await _lookups(ChangeKind.PR, ()) == 0  # sin agentes esperados no hay nada que comparar
    assert await _lookups(ChangeKind.COMMIT, AGENTS) == 0  # un commit nunca reutiliza
