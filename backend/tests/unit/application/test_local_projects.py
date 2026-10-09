from __future__ import annotations

import logging
from uuid import UUID, uuid4

import pytest

from duelo.application import local_projects
from duelo.application.ingest_commit import (
    ChangeSubmission,
    IngestResult,
    ProjectNotFound,
    ingest_pr,
)
from duelo.application.local_projects import (
    ProjectHasNoFolder,
    SyncResult,
    add_local_project,
    remove_local_project,
    sync_all_pull_requests,
    sync_pull_requests,
)
from duelo.application.ports import (
    GithubUnavailable,
    HookInstallError,
    InvalidRepository,
    ProjectAlreadyExists,
    RepoInfo,
)
from duelo.domain.change import MAX_REF
from duelo.domain.project import Project
from tests.fakes.change_repository import FakeChangeRepository
from tests.fakes.event_log import FakeEventLog
from tests.fakes.local_projects import (
    FakeGithubPrSource,
    FakeGitRepository,
    FakeHookInstaller,
    pull_request,
)
from tests.fakes.project_repository import FakeProjectRepository
from tests.fakes.review_repository import FakeReviewRepository
from tests.fakes.review_starter import FakeReviewStarter

ROOT = "/home/u/widgets"


def _repo(remote: str | None = "git@github.com:acme/widgets.git") -> FakeGitRepository:
    return FakeGitRepository(RepoInfo(root=ROOT, remote_url=remote))


# --- alta ---------------------------------------------------------------------------------


async def test_adding_registers_the_project_and_installs_the_hooks() -> None:
    catalog, hooks = FakeProjectRepository(), FakeHookInstaller()

    project = await add_local_project(_repo(), hooks, catalog, ROOT)

    assert (project.slug, project.path, project.hooks_installed, project.github) == (
        "acme/widgets",
        ROOT,
        True,
        True,
    )
    assert isinstance(project.id, UUID)
    assert await catalog.get_by_slug("acme/widgets") == project
    assert hooks.installed == [(ROOT, "acme/widgets")]


async def test_without_a_github_remote_the_folder_name_is_the_slug() -> None:
    project = await add_local_project(
        _repo(remote=None), FakeHookInstaller(), FakeProjectRepository(), ROOT
    )

    assert (project.slug, project.github) == ("widgets", False)


async def test_the_path_is_inspected_exactly_as_received() -> None:
    git = _repo()

    await add_local_project(git, FakeHookInstaller(), FakeProjectRepository(), "/x/y")

    assert git.inspected == ["/x/y"]


async def test_an_invalid_repository_registers_nothing_and_writes_no_hooks() -> None:
    catalog, hooks = FakeProjectRepository(), FakeHookInstaller()

    with pytest.raises(InvalidRepository, match="no es un repo"):
        await add_local_project(FakeGitRepository(error="no es un repo"), hooks, catalog, ROOT)

    assert await catalog.list_all() == [] and hooks.installed == []


async def test_a_folder_name_that_cannot_be_a_slug_is_an_invalid_repository() -> None:
    git = FakeGitRepository(RepoInfo(root="/home/u/mi repo", remote_url=None))
    catalog, hooks = FakeProjectRepository(), FakeHookInstaller()

    with pytest.raises(InvalidRepository, match="No se puede usar 'mi repo'"):
        await add_local_project(git, hooks, catalog, "/home/u/mi repo")

    assert await catalog.list_all() == [] and hooks.installed == []


async def test_a_repeated_slug_is_a_conflict_that_does_not_touch_the_disk() -> None:
    existing = Project(id=uuid4(), slug="acme/widgets", path="/otra")
    catalog, hooks = FakeProjectRepository(existing), FakeHookInstaller()

    with pytest.raises(ProjectAlreadyExists):
        await add_local_project(_repo(), hooks, catalog, ROOT)

    assert hooks.installed == []
    assert await catalog.get_by_slug("acme/widgets") == existing


async def test_a_repeated_folder_is_a_conflict() -> None:
    catalog = FakeProjectRepository()
    await add_local_project(_repo(), FakeHookInstaller(), catalog, ROOT)

    with pytest.raises(ProjectAlreadyExists):
        await add_local_project(_repo(remote=None), FakeHookInstaller(), catalog, ROOT)


async def test_when_the_hooks_fail_the_project_is_not_left_registered() -> None:
    catalog = FakeProjectRepository()

    with pytest.raises(HookInstallError, match="no es shell"):
        await add_local_project(
            _repo(), FakeHookInstaller(install_error="no es shell"), catalog, ROOT
        )

    assert await catalog.list_all() == []


# --- baja ---------------------------------------------------------------------------------


async def test_removing_uninstalls_the_hooks_and_deletes_the_project() -> None:
    catalog, hooks = FakeProjectRepository(), FakeHookInstaller()
    await add_local_project(_repo(), hooks, catalog, ROOT)

    await remove_local_project(hooks, catalog, "acme/widgets")

    assert hooks.uninstalled == [ROOT]
    assert await catalog.list_all() == []


async def test_removing_an_unknown_project_is_not_found() -> None:
    hooks = FakeHookInstaller()

    with pytest.raises(ProjectNotFound) as caught:
        await remove_local_project(hooks, FakeProjectRepository(), "no/existe")

    assert caught.value.slug == "no/existe"

    assert hooks.uninstalled == []


async def test_a_project_without_folder_is_removed_without_touching_any_hooks() -> None:
    plain = Project(id=uuid4(), slug="solo/db")
    catalog, hooks = FakeProjectRepository(plain), FakeHookInstaller()

    await remove_local_project(hooks, catalog, "solo/db")

    assert hooks.uninstalled == [] and await catalog.list_all() == []


async def test_a_failure_cleaning_the_hooks_does_not_prevent_the_removal() -> None:
    catalog = FakeProjectRepository()
    await add_local_project(_repo(), FakeHookInstaller(), catalog, ROOT)

    await remove_local_project(FakeHookInstaller(uninstall_fails=True), catalog, "acme/widgets")

    assert await catalog.list_all() == []


# --- sincronización de PRs -----------------------------------------------------------------


class _Ingest:
    """`ingest_pr` real sobre repositorios en memoria."""

    def __init__(self, catalog: FakeProjectRepository) -> None:
        events = FakeEventLog()
        self.changes = FakeChangeRepository(FakeReviewRepository(events), events)
        self.catalog = catalog
        self.starter = FakeReviewStarter()

    async def __call__(self, submission: ChangeSubmission) -> IngestResult:
        return await ingest_pr(
            self.catalog, self.changes, self.starter, submission, max_diff_chars=200_000
        )


async def _local_catalog() -> FakeProjectRepository:
    catalog = FakeProjectRepository()
    await add_local_project(_repo(), FakeHookInstaller(), catalog, ROOT)
    return catalog


async def test_sync_registers_each_open_pr_as_a_pr_change() -> None:
    catalog = await _local_catalog()
    github = FakeGithubPrSource([pull_request(1), pull_request(2)])
    ingest = _Ingest(catalog)

    result = await sync_pull_requests(catalog, github, ingest, "acme/widgets")

    assert result == SyncResult(synced=2, created=2)
    assert github.queried == [ROOT]
    assert sorted(c.kind.value for c in ingest.starter.started.values()) == ["pr", "pr"]
    assert {c.title for c in ingest.starter.started.values()} == {"feat: pr 1", "feat: pr 2"}


async def test_sync_forwards_every_field_of_the_pr() -> None:
    catalog = await _local_catalog()
    pr = pull_request(7, author="luis", ref="feature-x", head_sha="b" * 40)
    ingest = _Ingest(catalog)

    await sync_pull_requests(catalog, FakeGithubPrSource([pr]), ingest, "acme/widgets")

    (change,) = ingest.starter.started.values()
    assert (change.ref, change.head_sha, change.author, change.url, change.diff) == (
        "feature-x",
        "b" * 40,
        "luis",
        pr.url,
        pr.diff,
    )


async def test_sync_twice_creates_nothing_the_second_time() -> None:
    catalog = await _local_catalog()
    github = FakeGithubPrSource([pull_request(1), pull_request(2)])
    ingest = _Ingest(catalog)
    await sync_pull_requests(catalog, github, ingest, "acme/widgets")

    again = await sync_pull_requests(catalog, github, ingest, "acme/widgets")

    assert again == SyncResult(synced=2, created=0)


async def test_sync_counts_only_the_new_prs() -> None:
    catalog = await _local_catalog()
    ingest = _Ingest(catalog)
    await sync_pull_requests(catalog, FakeGithubPrSource([pull_request(1)]), ingest, "acme/widgets")

    result = await sync_pull_requests(
        catalog, FakeGithubPrSource([pull_request(1), pull_request(2)]), ingest, "acme/widgets"
    )

    assert result == SyncResult(synced=2, created=1)


async def test_sync_skips_a_pr_that_breaks_the_domain_limits_and_keeps_the_rest() -> None:
    catalog = await _local_catalog()
    github = FakeGithubPrSource([pull_request(1, ref="r" * (MAX_REF + 1)), pull_request(2)])

    result = await sync_pull_requests(catalog, github, _Ingest(catalog), "acme/widgets")

    assert result == SyncResult(synced=1, created=1)


async def test_sync_of_an_unknown_project_is_not_found() -> None:
    with pytest.raises(ProjectNotFound) as caught:
        await sync_pull_requests(
            FakeProjectRepository(), FakeGithubPrSource(), _Ingest(FakeProjectRepository()), "x/y"
        )

    assert caught.value.slug == "x/y"


async def test_sync_of_a_project_without_folder_is_refused_before_asking_github() -> None:
    plain = Project(id=uuid4(), slug="solo/db")
    catalog, github = FakeProjectRepository(plain), FakeGithubPrSource([pull_request(1)])

    with pytest.raises(ProjectHasNoFolder, match="solo/db no tiene carpeta local") as caught:
        await sync_pull_requests(catalog, github, _Ingest(catalog), "solo/db")

    assert caught.value.slug == "solo/db"

    assert github.queried == []


async def test_sync_propagates_github_being_unavailable() -> None:
    catalog = await _local_catalog()

    with pytest.raises(GithubUnavailable, match="sin gh"):
        await sync_pull_requests(
            catalog, FakeGithubPrSource(unavailable="sin gh"), _Ingest(catalog), "acme/widgets"
        )


async def test_sync_all_goes_through_every_local_project_and_survives_failures() -> None:
    catalog = FakeProjectRepository()
    for slug, path in (("a/one", "/p/one"), ("b/two", "/p/two"), ("c/three", "/p/three")):
        await catalog.add_local(Project(id=uuid4(), slug=slug, path=path))
    await catalog.add_local(Project(id=uuid4(), slug="sin/carpeta"))
    seen: list[str] = []

    async def sync(slug: str) -> SyncResult:
        seen.append(slug)
        if slug == "b/two":
            raise GithubUnavailable("sin sesión")
        return SyncResult(synced=1, created=1)

    results = await sync_all_pull_requests(catalog, sync)

    assert seen == ["a/one", "b/two", "c/three"]  # sin carpeta no se toca y el fallo no corta
    assert results == {"a/one": SyncResult(1, 1), "c/three": SyncResult(1, 1)}


# --- lo que queda en el log cuando algo no se puede hacer -------------------------------------


@pytest.fixture
def log(
    caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch
) -> pytest.LogCaptureFixture:
    # `alembic` (fileConfig) deshabilita los loggers ya creados si un test de migraciones corrió
    # antes en el mismo proceso: aquí se vuelve a habilitar el que se comprueba.
    monkeypatch.setattr(local_projects.logger, "disabled", False)
    caplog.set_level(logging.WARNING, logger=local_projects.logger.name)
    return caplog


async def test_a_failed_hook_cleanup_is_logged_with_the_project(
    log: pytest.LogCaptureFixture,
) -> None:
    catalog = FakeProjectRepository()
    await add_local_project(_repo(), FakeHookInstaller(), catalog, ROOT)

    await remove_local_project(FakeHookInstaller(uninstall_fails=True), catalog, "acme/widgets")

    (record,) = log.records
    assert record.getMessage() == "No se pudieron quitar los hooks de acme/widgets"
    assert record.exc_info is not None  # con la traza de la causa


async def test_a_discarded_pr_is_logged_with_its_number_and_project(
    log: pytest.LogCaptureFixture,
) -> None:
    catalog = await _local_catalog()
    github = FakeGithubPrSource([pull_request(41, ref="r" * (MAX_REF + 1))])

    await sync_pull_requests(catalog, github, _Ingest(catalog), "acme/widgets")

    assert [r.getMessage() for r in log.records] == [
        "PR #41 de acme/widgets descartada: datos fuera de límites"
    ]


async def test_a_project_that_fails_to_sync_is_logged_with_its_name(
    log: pytest.LogCaptureFixture,
) -> None:
    catalog = await _local_catalog()

    async def sync(slug: str) -> SyncResult:
        raise GithubUnavailable("sin sesión")

    await sync_all_pull_requests(catalog, sync)

    (record,) = log.records
    assert record.getMessage() == "No se pudieron sincronizar las PRs de acme/widgets"
    assert record.exc_info is not None and "sin sesión" in log.text  # con la traza de la causa
