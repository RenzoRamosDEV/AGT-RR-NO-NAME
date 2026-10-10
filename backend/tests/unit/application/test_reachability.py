"""Barrido de alcanzabilidad: qué commits se marcan como deshechos y cuáles se recuperan."""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest

from duelo.application.reachability import SweepResult, sweep_all, sweep_project
from duelo.domain.change import Change, ChangeKind
from duelo.domain.events import ChangeCreated
from duelo.domain.project import Project
from tests.fakes.change_repository import FakeChangeRepository
from tests.fakes.commit_history import FakeCommitMarks, FakeRepositoryHistory
from tests.fakes.event_log import FakeChangeEventRepository, FakeEventLog
from tests.fakes.project_repository import FakeProjectRepository
from tests.fakes.review_repository import FakeReviewRepository

T0 = datetime(2026, 1, 1, tzinfo=UTC)
NOW = T0 + timedelta(days=30)
SHA_A, SHA_B, SHA_C = "a" * 40, "b" * 40, "c" * 40
PATH = "/home/u/widgets"


class Fixture:
    def __init__(self) -> None:
        self.events = FakeEventLog()
        self.changes = FakeChangeRepository(FakeReviewRepository(self.events), self.events)
        self.history = FakeRepositoryHistory()
        self.marks = FakeCommitMarks(self.changes, self.events)
        self.project = Project(id=uuid4(), slug="acme/widgets", path=PATH)
        self.catalog = FakeProjectRepository(self.project)

    async def add(
        self,
        sha: str,
        *,
        kind: ChangeKind = ChangeKind.COMMIT,
        created_at: datetime = T0,
        project: Project | None = None,
    ) -> Change:
        owner = project or self.project
        change = Change.new(
            project_id=owner.id,
            kind=kind,
            ref="main",
            head_sha=sha,
            title="t",
            author="a",
            url="",
            diff="",
            diff_truncated=False,
            created_at=created_at,
        )
        event = ChangeCreated(
            change_id=change.id, project_id=owner.id, kind=kind.value, head_sha=sha
        )
        return await self.changes.add(change, event)

    async def state_of(self, change: Change) -> bool:
        """`True` si el change está marcado como deshecho."""
        stored = await self.changes.get(change.id)
        assert stored is not None
        return stored.discarded_at is not None

    async def event_types(self, change: Change) -> list[str]:
        events = FakeChangeEventRepository(self.events)
        return [e.type for e in await events.list_for_change(self.project.id, change.id)]

    async def sweep(self, *, window: int = 5000) -> SweepResult:
        return await sweep_project(self.history, self.marks, self.project, window=window, now=NOW)


async def test_a_commit_that_is_no_longer_reachable_is_marked_as_discarded() -> None:
    f = Fixture()
    lost, kept = await f.add(SHA_A), await f.add(SHA_B)
    f.history.set_reachable(PATH, [SHA_B])

    result = await f.sweep()

    assert result == SweepResult(discarded=1, restored=0)
    assert await f.state_of(lost) is True
    assert await f.state_of(kept) is False
    stored = await f.changes.get(lost.id)
    assert stored is not None and stored.discarded_at == NOW
    assert await f.event_types(lost) == ["change.created", "commit.discarded"]


async def test_a_discarded_commit_that_is_reachable_again_is_restored() -> None:
    f = Fixture()
    change = await f.add(SHA_A)
    f.history.set_reachable(PATH, [])
    await f.sweep()
    f.history.set_reachable(PATH, [SHA_A])

    result = await f.sweep()

    assert result == SweepResult(discarded=0, restored=1)
    assert await f.state_of(change) is False
    assert await f.event_types(change) == ["change.created", "commit.discarded", "commit.restored"]


async def test_sweeping_twice_marks_once_and_emits_one_event() -> None:
    f = Fixture()
    change = await f.add(SHA_A)
    f.history.set_reachable(PATH, [])

    first = await f.sweep()
    second = await f.sweep()

    assert (first, second) == (SweepResult(1, 0), SweepResult(0, 0))
    assert await f.event_types(change) == ["change.created", "commit.discarded"]
    assert f.marks.apply_calls == 1  # el segundo barrido no tenía nada que cambiar


async def test_nothing_is_written_when_every_commit_is_reachable() -> None:
    f = Fixture()
    await f.add(SHA_A)
    f.history.set_reachable(PATH, [SHA_A])

    result = await f.sweep()

    assert result == SweepResult(0, 0)
    assert f.marks.apply_calls == 0


async def test_a_pr_is_never_evaluated() -> None:
    f = Fixture()
    pr = await f.add(SHA_A, kind=ChangeKind.PR)
    f.history.set_reachable(PATH, [])

    result = await f.sweep()

    assert result == SweepResult(0, 0)
    assert await f.state_of(pr) is False


async def test_a_project_without_a_folder_is_not_swept_and_git_is_not_asked() -> None:
    f = Fixture()
    no_folder = Project(id=uuid4(), slug="acme/remote-only")
    await f.add(SHA_A, project=no_folder)

    result = await sweep_project(f.history, f.marks, no_folder, window=5000, now=NOW)

    assert (result.discarded, result.restored) == (0, 0)
    assert f.history.reachable_calls == []


async def test_a_project_with_no_commits_does_not_ask_git() -> None:
    f = Fixture()

    result = await f.sweep()

    assert result == SweepResult(0, 0)
    assert f.history.reachable_calls == []


async def test_the_window_is_passed_to_git() -> None:
    f = Fixture()
    await f.add(SHA_A)
    f.history.set_reachable(PATH, [SHA_A])

    await f.sweep(window=123)

    assert f.history.reachable_calls == [(PATH, 123)]


async def test_the_changes_are_read_before_asking_git() -> None:
    """Un commit ingerido entre ambos pasos no debe parecer «deshecho» por no estar en una foto
    anterior de git: la lista de changes se lee primero."""
    f = Fixture()
    await f.add(SHA_A)
    f.history.set_reachable(PATH, [SHA_A])
    order: list[str] = []
    real_tracked, real_reachable = f.marks.tracked_commits, f.history.reachable

    async def tracked(project_id: UUID):  # type: ignore[no-untyped-def]
        order.append("changes")
        return await real_tracked(project_id)

    async def reachable(path: str, *, limit: int):  # type: ignore[no-untyped-def]
        order.append("git")
        return await real_reachable(path, limit=limit)

    f.marks.tracked_commits = tracked  # type: ignore[method-assign]
    f.history.reachable = reachable  # type: ignore[method-assign]

    await f.sweep()

    assert order == ["changes", "git"]


# --- ventana llena --------------------------------------------------------------------------


async def test_with_a_full_window_a_candidate_that_git_still_holds_is_not_marked() -> None:
    """Un commit anterior a la ventana ingerido tarde (recuperado por `pre-push`) es alcanzable
    aunque no esté en la lista: la comprobación individual lo salva."""
    f = Fixture()
    late = await f.add(SHA_A, created_at=T0 + timedelta(days=20))
    f.history.set_reachable(PATH, [SHA_B], truncated=True, oldest_at=T0 + timedelta(days=10))
    f.history.set_contained(PATH, [SHA_A])

    await f.sweep()

    assert await f.state_of(late) is False
    assert f.history.contains_calls == [(PATH, SHA_A)]


async def test_with_a_full_window_a_candidate_git_no_longer_holds_is_marked() -> None:
    f = Fixture()
    lost = await f.add(SHA_A, created_at=T0 + timedelta(days=20))
    f.history.set_reachable(PATH, [SHA_B], truncated=True, oldest_at=T0 + timedelta(days=10))

    await f.sweep()

    assert await f.state_of(lost) is True


async def test_with_a_full_window_changes_older_than_it_are_not_even_confirmed() -> None:
    f = Fixture()
    old = await f.add(SHA_A, created_at=T0)
    f.history.set_reachable(PATH, [SHA_B], truncated=True, oldest_at=T0 + timedelta(days=10))

    await f.sweep()

    assert await f.state_of(old) is False
    assert f.history.contains_calls == []


async def test_with_a_complete_set_no_individual_confirmation_is_needed() -> None:
    f = Fixture()
    await f.add(SHA_A)
    f.history.set_reachable(PATH, [])

    await f.sweep()

    assert f.history.contains_calls == []


# --- errores ---------------------------------------------------------------------------------


async def test_a_broken_repository_marks_nothing_and_the_others_are_still_swept() -> None:
    f = Fixture()
    other = Project(id=uuid4(), slug="acme/other", path="/home/u/other")
    f.catalog = FakeProjectRepository(f.project, other)
    mine = await f.add(SHA_A)
    theirs = await f.add(SHA_B, project=other)
    f.history.break_repository(PATH)
    f.history.set_reachable(other.path or "", [])

    results = await sweep_all(f.catalog, f.history, f.marks, window=5000, clock=lambda: NOW)

    assert await f.state_of(mine) is False  # el repo roto no marca nada
    assert await f.state_of(theirs) is True  # el otro proyecto sí se barrió
    assert results == {"acme/other": SweepResult(discarded=1, restored=0)}


async def test_an_unexpected_error_in_one_project_does_not_stop_the_sweep() -> None:
    f = Fixture()
    other = Project(id=uuid4(), slug="acme/other", path="/home/u/other")
    f.catalog = FakeProjectRepository(f.project, other)
    await f.add(SHA_A)
    theirs = await f.add(SHA_B, project=other)
    f.history.set_reachable(other.path or "", [])
    real = f.history.reachable

    async def explode(path: str, *, limit: int):  # type: ignore[no-untyped-def]
        if path == PATH:
            raise RuntimeError("fallo inesperado")
        return await real(path, limit=limit)

    f.history.reachable = explode  # type: ignore[method-assign]

    await sweep_all(f.catalog, f.history, f.marks, window=5000, clock=lambda: NOW)

    assert await f.state_of(theirs) is True


async def test_sweep_all_only_visits_projects_with_a_folder() -> None:
    f = Fixture()
    no_folder = Project(id=uuid4(), slug="acme/remote-only")
    f.catalog = FakeProjectRepository(f.project, no_folder)
    await f.add(SHA_A)
    f.history.set_reachable(PATH, [SHA_A])

    results = await sweep_all(f.catalog, f.history, f.marks, window=5000, clock=lambda: NOW)

    assert results == {"acme/widgets": SweepResult(0, 0)}
    assert [p for p, _ in f.history.reachable_calls] == [PATH]


async def test_sweep_all_passes_the_window_and_the_clock_to_every_project() -> None:
    f = Fixture()
    lost = await f.add(SHA_A)
    f.history.set_reachable(PATH, [])

    await sweep_all(f.catalog, f.history, f.marks, window=321, clock=lambda: NOW)

    assert f.history.reachable_calls == [(PATH, 321)]
    stored = await f.changes.get(lost.id)
    assert stored is not None and stored.discarded_at == NOW


async def test_sweep_all_uses_the_real_clock_by_default() -> None:
    f = Fixture()
    lost = await f.add(SHA_A)
    f.history.set_reachable(PATH, [])
    before = datetime.now(UTC)

    await sweep_all(f.catalog, f.history, f.marks, window=5000)

    stored = await f.changes.get(lost.id)
    assert stored is not None and stored.discarded_at is not None
    assert before <= stored.discarded_at <= datetime.now(UTC)


@pytest.fixture
def sweep_log(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> pytest.LogCaptureFixture:
    """El `fileConfig` de alembic (tests de integración) desactiva los loggers existentes; se
    deja el del barrido como lo deja la app, con independencia del orden de los tests."""
    logger = logging.getLogger("duelo.application.reachability")
    monkeypatch.setattr(logger, "disabled", False)
    monkeypatch.setattr(logger, "propagate", True)
    caplog.set_level(logging.WARNING, logger=logger.name)
    return caplog


async def test_an_unavailable_repository_is_logged_with_the_project_and_the_trace(
    sweep_log: pytest.LogCaptureFixture,
) -> None:
    f = Fixture()
    await f.add(SHA_A)
    f.history.break_repository(PATH)

    await sweep_all(f.catalog, f.history, f.marks, window=5000, clock=lambda: NOW)

    (record,) = sweep_log.records
    assert "acme/widgets" in record.getMessage()
    assert "historial" in record.getMessage()
    assert record.exc_info is not None  # lleva la traza


async def test_an_unexpected_failure_is_logged_with_the_project_and_the_trace(
    sweep_log: pytest.LogCaptureFixture,
) -> None:
    f = Fixture()
    await f.add(SHA_A)

    async def explode(path: str, *, limit: int):  # type: ignore[no-untyped-def]
        raise RuntimeError("fallo inesperado")

    f.history.reachable = explode  # type: ignore[method-assign]

    await sweep_all(f.catalog, f.history, f.marks, window=5000, clock=lambda: NOW)

    (record,) = sweep_log.records
    assert "acme/widgets" in record.getMessage()
    assert "barrido" in record.getMessage()
    assert record.exc_info is not None


@pytest.mark.parametrize("sha", ["abc1234", "A" * 40])
async def test_stored_shas_are_matched_in_lowercase(sha: str) -> None:
    f = Fixture()
    change = await f.add(sha)
    f.history.set_reachable(PATH, [sha.lower()])

    await f.sweep()

    assert await f.state_of(change) is False
