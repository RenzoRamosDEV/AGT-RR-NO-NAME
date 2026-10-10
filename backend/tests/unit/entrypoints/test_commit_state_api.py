"""Contrato HTTP de los commits deshechos y revertidos: `commit_state` y `reverted_by` en el listado
y en el detalle, el campo opcional `body` de la ingesta y los eventos de la línea de tiempo."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

import httpx
import pytest

from tests.fakes.api import FakeApi, build_fake_api, valid_body

HEADERS = {"X-Ingest-Token": "s3cr3t-token"}
SHA_A, SHA_B = "a" * 40, "b" * 40
NOW = datetime(2026, 1, 1, tzinfo=UTC)


def _client(api: FakeApi) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=api.app, raise_app_exceptions=False),
        base_url="http://test",
    )


async def _ingest(client: httpx.AsyncClient, sha: str, **overrides: object) -> str:
    # Como `git revert`: un mensaje que revierte lleva título `Revert "…"`.
    if "This reverts commit" in str(overrides.get("body", "")):
        overrides.setdefault("title", 'Revert "feat: algo"')
    response = await client.post(
        "/ingest/commit", json=valid_body(head_sha=sha, **overrides), headers=HEADERS
    )
    assert response.status_code == 202, response.text
    return response.json()["change_id"]


async def _listing(client: httpx.AsyncClient) -> dict[str, dict[str, object]]:
    items = (await client.get("/projects/acme/widgets/changes")).json()["items"]
    return {item["head_sha"]: item for item in items}


async def _ids(client: httpx.AsyncClient) -> dict[str, str]:
    return {sha: str(item["id"]) for sha, item in (await _listing(client)).items()}


async def test_a_normal_commit_is_active_and_has_no_reverter() -> None:
    api = build_fake_api()
    async with _client(api) as client:
        change_id = await _ingest(client, SHA_A)

        listed = (await _listing(client))[SHA_A]
        detail = (await client.get(f"/changes/{change_id}")).json()

    for body in (listed, detail):
        assert body["commit_state"] == "active"
        assert body["reverted_by"] is None


async def test_a_discarded_commit_shows_as_discarded_in_the_listing_and_the_detail() -> None:
    api = build_fake_api()
    async with _client(api) as client:
        change_id = await _ingest(client, SHA_A)
        api.changes.mark_discarded(UUID(change_id), NOW)

        listed = (await _listing(client))[SHA_A]
        detail = (await client.get(f"/changes/{change_id}")).json()

    assert listed["commit_state"] == "discarded"
    assert detail["commit_state"] == "discarded"


async def test_a_reverted_commit_names_the_commit_that_reverts_it() -> None:
    api = build_fake_api()
    async with _client(api) as client:
        original = await _ingest(client, SHA_A, title="feat: login")
        revert = await _ingest(
            client,
            SHA_B,
            title='Revert "feat: login"',
            body=f"This reverts commit {SHA_A}.\n\nRompe el acceso.",
        )

        listed = await _listing(client)
        detail = (await client.get(f"/changes/{original}")).json()

    expected = {"id": revert, "head_sha": SHA_B}
    assert listed[SHA_A]["commit_state"] == "reverted"
    assert listed[SHA_A]["reverted_by"] == expected
    assert detail["commit_state"] == "reverted"
    assert detail["reverted_by"] == expected
    assert listed[SHA_B]["commit_state"] == "active"


async def test_discarded_wins_over_reverted_in_the_response() -> None:
    api = build_fake_api()
    async with _client(api) as client:
        original = await _ingest(client, SHA_A)
        await _ingest(client, SHA_B, body=f"This reverts commit {SHA_A}.")
        api.changes.mark_discarded(UUID(original), NOW)

        listed = (await _listing(client))[SHA_A]

    assert listed["commit_state"] == "discarded"
    assert listed["reverted_by"] is not None  # el dato del revert se conserva


async def test_a_revert_that_was_itself_undone_no_longer_reverts_the_original() -> None:
    """Si el commit de revert se deshace (`reset`), el original vuelve a estar en la rama."""
    api = build_fake_api()
    async with _client(api) as client:
        original = await _ingest(client, SHA_A)
        revert = await _ingest(client, SHA_B, body=f"This reverts commit {SHA_A}.")
        api.changes.mark_discarded(UUID(revert), NOW)

        listed = (await _listing(client))[SHA_A]
        detail = (await client.get(f"/changes/{original}")).json()

    for body in (listed, detail):
        assert body["commit_state"] == "active"
        assert body["reverted_by"] is None


async def test_a_revert_that_comes_back_reverts_the_original_again() -> None:
    api = build_fake_api()
    async with _client(api) as client:
        await _ingest(client, SHA_A)
        revert = await _ingest(client, SHA_B, body=f"This reverts commit {SHA_A}.")
        api.changes.mark_discarded(UUID(revert), NOW)
        api.changes.mark_discarded(UUID(revert), None)  # `git reset` de vuelta

        listed = (await _listing(client))[SHA_A]

    assert listed["commit_state"] == "reverted"
    assert listed["reverted_by"]["id"] == revert  # type: ignore[index]


@pytest.mark.parametrize("discard_old_first", [True, False])
async def test_an_amended_revert_takes_the_place_of_the_discarded_one(
    discard_old_first: bool,
) -> None:
    """`git commit --amend` sobre el revert deja otro SHA con el mismo mensaje: el original pasa a
    estar revertido por el nuevo, llegue antes el commit nuevo o la marca del antiguo."""
    api = build_fake_api()
    body = f"This reverts commit {SHA_A}."
    async with _client(api) as client:
        await _ingest(client, SHA_A)
        old_revert = await _ingest(client, SHA_B, body=body)
        if discard_old_first:
            api.changes.mark_discarded(UUID(old_revert), NOW)
        new_revert = await _ingest(client, "c" * 40, body=body)
        if not discard_old_first:
            api.changes.mark_discarded(UUID(old_revert), NOW)  # el barrido llega después
        listed = (await _listing(client))[SHA_A]
        detail = (await client.get(f"/changes/{(await _ids(client))[SHA_A]}")).json()

    expected = {"id": new_revert, "head_sha": "c" * 40}
    for body_ in (listed, detail):
        assert body_["commit_state"] == "reverted"
        assert body_["reverted_by"] == expected


async def test_a_pr_is_always_active() -> None:
    api = build_fake_api()
    async with _client(api) as client:
        response = await client.post("/ingest/pr", json=valid_body(head_sha=SHA_A), headers=HEADERS)
        pr_id = UUID(response.json()["change_id"])
        api.changes.mark_discarded(pr_id, NOW)  # aunque alguien la marcara, una PR no cambia

        listed = (await _listing(client))[SHA_A]

    assert listed["commit_state"] == "active"


async def test_the_state_does_not_change_the_review_status() -> None:
    api = build_fake_api()
    async with _client(api) as client:
        change_id = await _ingest(client, SHA_A)
        before = (await client.get(f"/changes/{change_id}")).json()["review_status"]
        api.changes.mark_discarded(UUID(change_id), NOW)

        after = (await client.get(f"/changes/{change_id}")).json()["review_status"]

    assert before == after == "pending"


async def test_the_timeline_of_a_reverted_commit_includes_commit_reverted() -> None:
    api = build_fake_api()
    async with _client(api) as client:
        original = await _ingest(client, SHA_A)
        await _ingest(client, SHA_B, body=f"This reverts commit {SHA_A}.")

        events = (await client.get(f"/changes/{original}/events")).json()

    assert [e["type"] for e in events] == ["change.created", "commit.reverted"]


async def test_the_timeline_exposes_discarded_and_restored_events_without_internal_data() -> None:
    api = build_fake_api()
    async with _client(api) as client:
        change_id = await _ingest(client, SHA_A)
        for event_type in ("commit.discarded", "commit.restored"):
            api.events.append_raw(
                project_id=api.project.id,
                type=event_type,
                payload={"change_id": change_id, "project_id": str(api.project.id), "secret": "x"},
            )

        events = (await client.get(f"/changes/{change_id}/events")).json()

    assert [e["type"] for e in events] == ["change.created", "commit.discarded", "commit.restored"]
    assert all("secret" not in e for e in events)


async def test_a_request_without_body_is_still_accepted() -> None:
    """Los hooks instalados antes de este campo no lo envían."""
    api = build_fake_api()
    body = valid_body(head_sha=SHA_A)
    assert "body" not in body
    async with _client(api) as client:
        response = await client.post("/ingest/commit", json=body, headers=HEADERS)

    assert response.status_code == 202


async def test_a_body_over_the_limit_is_rejected_with_422() -> None:
    api = build_fake_api()
    async with _client(api) as client:
        response = await client.post(
            "/ingest/commit",
            json=valid_body(head_sha=SHA_A, body="x" * 20_001),
            headers=HEADERS,
        )

    assert response.status_code == 422


async def test_a_body_at_the_limit_is_accepted() -> None:
    api = build_fake_api()
    async with _client(api) as client:
        response = await client.post(
            "/ingest/commit",
            json=valid_body(head_sha=SHA_A, body="x" * 20_000),
            headers=HEADERS,
        )

    assert response.status_code == 202


async def test_an_unknown_field_is_still_rejected() -> None:
    api = build_fake_api()
    async with _client(api) as client:
        response = await client.post(
            "/ingest/commit", json=valid_body(head_sha=SHA_A, nope="x"), headers=HEADERS
        )

    assert response.status_code == 422
