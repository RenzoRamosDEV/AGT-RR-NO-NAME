"""Reviews ligeras en el listado del canal y agentes configurados en el diagnóstico."""

from datetime import UTC, datetime, timedelta

import httpx

from duelo.domain.change import Change, ChangeKind
from duelo.domain.events import ChangeCreated, ReviewCompleted, ReviewFailed
from duelo.domain.review import Finding, Review, ReviewResult
from tests.fakes.api import FakeApi, build_fake_api

T0 = datetime(2026, 1, 1, tzinfo=UTC)
BRIEF_KEYS = {"agent", "status", "score", "duration_ms", "run"}


def _client(api: FakeApi) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=api.app, raise_app_exceptions=False),
        base_url="http://test",
    )


async def _add_change(api: FakeApi, i: int) -> Change:
    change = Change.new(
        project_id=api.project.id,
        kind=ChangeKind.COMMIT,
        ref="refs/heads/main",
        head_sha=f"{i:x}".rjust(40, "0"),
        title=f"change {i}",
        author="renzo",
        url="https://example.com",
        diff="DIFF COMPLETO",
        diff_truncated=False,
        created_at=T0 + timedelta(minutes=i),
    )
    event = ChangeCreated(
        change_id=change.id, project_id=api.project.id, kind="commit", head_sha=change.head_sha
    )
    return await api.changes.add(change, event)


async def _review(
    api: FakeApi, change: Change, agent: str, *, run: int, fail: bool = False
) -> None:
    ids = {"change_id": change.id, "project_id": api.project.id, "agent": agent}
    common = {"change_id": change.id, "agent": agent, "run": run, "created_at": T0}
    if fail:
        review = Review.failed(error="BOOM interno", duration_ms=7, **common)
        await api.reviews.add(review, ReviewFailed(review_id=review.id, error="BOOM", **ids))
        return
    result = ReviewResult(
        summary="RESUMEN LARGO",
        score=8,
        findings=(Finding(severity="bug", file="a.py", line=3, message="HALLAZGO"),),
    )
    review = Review.succeeded(result=result, raw_output="SALIDA CRUDA", duration_ms=42, **common)
    await api.reviews.add(review, ReviewCompleted(review_id=review.id, **ids))


async def _items(api: FakeApi) -> list[dict]:
    async with _client(api) as client:
        response = await client.get(f"/projects/{api.project.slug}/changes")
    assert response.status_code == 200, response.text
    return response.json()["items"]


async def test_channel_items_carry_light_reviews_without_findings_diff_or_raw_output() -> None:
    api = build_fake_api()
    change = await _add_change(api, 1)
    await _review(api, change, "b_agent", run=1)
    await _review(api, change, "a_agent", run=1, fail=True)

    (item,) = await _items(api)

    # Ordenadas por agente y con SOLO los campos ligeros.
    assert [r["agent"] for r in item["reviews"]] == ["a_agent", "b_agent"]
    assert all(set(r) == BRIEF_KEYS for r in item["reviews"])
    assert {r["agent"]: (r["status"], r["score"], r["duration_ms"]) for r in item["reviews"]} == {
        "a_agent": ("failed", None, 7),
        "b_agent": ("completed", 8, 42),
    }
    for heavy in ("RESUMEN LARGO", "HALLAZGO", "SALIDA CRUDA", "BOOM", "DIFF COMPLETO"):
        assert heavy not in str(item)
    assert "diff" not in item and "findings" not in item


async def test_channel_reviews_only_include_the_current_run() -> None:
    """Tras un reintento el canal no debe mostrar la review del run anterior."""
    api = build_fake_api()
    change = await _add_change(api, 1)
    await _review(api, change, "agent_1", run=1, fail=True)
    advanced = await api.changes.advance_run(change.id, from_run=1, started_at=T0)
    assert advanced is not None and advanced.run == 2
    await _review(api, advanced, "agent_1", run=2)

    (item,) = await _items(api)

    assert [(r["run"], r["status"]) for r in item["reviews"]] == [(2, "completed")]


async def test_a_change_without_reviews_has_an_empty_list() -> None:
    api = build_fake_api()
    await _add_change(api, 1)

    (item,) = await _items(api)

    assert item["reviews"] == []


async def test_health_dependencies_report_the_configured_agent_names() -> None:
    """Origen: la UI mostraba «Claude, Codex» fijo aunque el backend use AGENT_NAMES."""
    api = build_fake_api(agent_names=["agent_1", "agent_2", "gemini"])

    async with _client(api) as client:
        response = await client.get("/health/dependencies")

    assert response.json()["agent_names"] == ["agent_1", "agent_2", "gemini"]
