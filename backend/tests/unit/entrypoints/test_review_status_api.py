"""Filtros `status`/`q` del canal, `review_status` y `findings_summary` del detalle."""

from datetime import UTC, datetime, timedelta

import httpx

from duelo.domain.change import Change, ChangeKind
from duelo.domain.events import ChangeCreated, ReviewCompleted, ReviewFailed
from duelo.domain.review import Finding, Review, ReviewResult
from tests.fakes.api import FakeApi, build_fake_api

T0 = datetime(2026, 1, 1, tzinfo=UTC)


def _client(api: FakeApi) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=api.app, raise_app_exceptions=False),
        base_url="http://test",
    )


async def _add_change(
    api: FakeApi, i: int, *, title: str = "", author: str = "renzo", ref: str = "refs/heads/main"
) -> Change:
    change = Change.new(
        project_id=api.project.id,
        kind=ChangeKind.COMMIT,
        ref=ref,
        head_sha=f"{i:x}".rjust(40, "0"),
        title=title or f"change {i}",
        author=author,
        url="https://example.com",
        diff="d",
        diff_truncated=False,
        created_at=T0 + timedelta(minutes=i),
    )
    event = ChangeCreated(
        change_id=change.id, project_id=api.project.id, kind="commit", head_sha=change.head_sha
    )
    return await api.changes.add(change, event)


async def _review(
    api: FakeApi,
    change: Change,
    agent: str,
    *,
    fail: bool = False,
    severities: tuple[str, ...] = (),
) -> None:
    ids = {"change_id": change.id, "project_id": api.project.id, "agent": agent}
    common = {"change_id": change.id, "agent": agent, "run": change.run, "created_at": T0}
    if fail:
        review = Review.failed(error="boom", duration_ms=None, **common)
        await api.reviews.add(review, ReviewFailed(review_id=review.id, error="boom", **ids))
        return
    findings = tuple(Finding(severity=s, file="a.py", line=1, message="m") for s in severities)
    review = Review.succeeded(
        result=ReviewResult(summary="ok", score=5, findings=findings),
        raw_output="SALIDA CRUDA",
        duration_ms=1,
        **common,
    )
    await api.reviews.add(review, ReviewCompleted(review_id=review.id, **ids))


async def _ids(client: httpx.AsyncClient, api: FakeApi, **params: object) -> list[str]:
    response = await client.get(f"/projects/{api.project.slug}/changes", params=params)
    assert response.status_code == 200, response.text
    return [item["id"] for item in response.json()["items"]]


async def test_channel_items_expose_review_status_and_filter_by_it() -> None:
    api = build_fake_api()
    done = await _add_change(api, 1)
    broken = await _add_change(api, 2)
    fresh = await _add_change(api, 3)
    for agent in ("a", "b"):
        await _review(api, done, agent)
        await _review(api, broken, agent, fail=True)

    async with _client(api) as client:
        everything = (await client.get(f"/projects/{api.project.slug}/changes")).json()["items"]
        failed = await _ids(client, api, status="failed")
        either = await _ids(client, api, status=["pending", "completed"])

    assert {i["id"]: i["review_status"] for i in everything} == {
        str(done.id): "completed",
        str(broken.id): "failed",
        str(fresh.id): "pending",
    }
    assert failed == [str(broken.id)]
    assert either == [str(fresh.id), str(done.id)]  # `status` es repetible


async def test_search_matches_title_author_sha_and_ref_ignoring_case() -> None:
    api = build_fake_api()
    by_title = await _add_change(api, 1, title="Arreglar el LOGIN")
    by_author = await _add_change(api, 2, author="Maria")
    by_ref = await _add_change(api, 3, ref="refs/heads/feature/pagos")
    by_sha = await _add_change(api, 0xABC)

    async with _client(api) as client:
        assert await _ids(client, api, q="login") == [str(by_title.id)]
        assert await _ids(client, api, q="MARIA") == [str(by_author.id)]
        assert await _ids(client, api, q="feature/pagos") == [str(by_ref.id)]
        assert await _ids(client, api, q="abc") == [str(by_sha.id)]
        assert await _ids(client, api, q="nada que coincida") == []


async def test_search_is_trimmed_and_blank_means_no_filter() -> None:
    api = build_fake_api()
    one = await _add_change(api, 1, title="uno")
    two = await _add_change(api, 2, title="dos")

    async with _client(api) as client:
        assert await _ids(client, api, q="  uno ") == [str(one.id)]
        assert await _ids(client, api, q="   ") == [str(two.id), str(one.id)]


async def test_filters_combine_with_each_other_and_with_kind() -> None:
    api = build_fake_api()
    target = await _add_change(api, 1, title="pagos roto")
    await _add_change(api, 2, title="pagos nuevo")  # pendiente: no cumple `status`
    other = await _add_change(api, 3, title="login roto")
    for change in (target, other):
        for agent in ("a", "b"):
            await _review(api, change, agent, fail=True)

    async with _client(api) as client:
        assert await _ids(client, api, status="failed", q="pagos") == [str(target.id)]
        assert await _ids(client, api, status="failed", q="pagos", kind="pr") == []


async def test_invalid_filters_are_422() -> None:
    api = build_fake_api()
    base = f"/projects/{api.project.slug}/changes"

    async with _client(api) as client:
        results = {
            "status desconocido": (await client.get(base, params={"status": "x"})).status_code,
            "q con NUL": (await client.get(base, params={"q": "a\x00b"})).status_code,
            "q de 100": (await client.get(base, params={"q": "a" * 100})).status_code,
            "q de 101": (await client.get(base, params={"q": "a" * 101})).status_code,
        }

    assert results == {
        "status desconocido": 422,
        "q con NUL": 422,
        "q de 100": 200,
        "q de 101": 422,
    }


async def test_nul_in_search_uses_the_standard_validation_format() -> None:
    api = build_fake_api()

    async with _client(api) as client:
        response = await client.get(f"/projects/{api.project.slug}/changes", params={"q": "a\x00b"})

    (error,) = response.json()["detail"]
    # El patrón del esquema (sin NUL) lo rechaza: así el contrato lo declara y no hay 500.
    assert error["loc"] == ["query", "q"] and error["type"] == "string_pattern_mismatch"


async def test_detail_includes_review_status_and_a_findings_summary_without_raw_output() -> None:
    api = build_fake_api()
    change = await _add_change(api, 1)
    await _review(api, change, "a", severities=("bug", "Risk", "banana"))
    await _review(api, change, "b", fail=True)

    async with _client(api) as client:
        response = await client.get(f"/changes/{change.id}")

    body = response.json()
    assert body["review_status"] == "partial_failed"
    assert body["findings_summary"] == {
        "total": 3,
        "by_severity": {"bug": 1, "risk": 1, "improvement": 0, "nit": 0, "other": 1},
    }
    assert "SALIDA CRUDA" not in response.text


async def test_detail_without_reviews_is_pending_with_an_all_zero_summary() -> None:
    api = build_fake_api()
    change = await _add_change(api, 1)

    async with _client(api) as client:
        body = (await client.get(f"/changes/{change.id}")).json()

    assert body["review_status"] == "pending"
    assert body["findings_summary"]["total"] == 0
    assert set(body["findings_summary"]["by_severity"].values()) == {0}
