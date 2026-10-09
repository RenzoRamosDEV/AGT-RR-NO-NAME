import pytest
from pydantic import ValidationError

from review_arena.config import Settings, WorkerSettings


def test_defaults_for_everything_but_the_token(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ("DATABASE_URL", "TEMPORAL_ADDRESS", "MAX_DIFF_CHARS", "AGENT_NAMES"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("INGEST_TOKEN", "t")

    settings = Settings()  # type: ignore[call-arg]

    assert settings.temporal_address == "localhost:7233"
    assert settings.max_diff_chars == 200_000
    assert settings.agent_names == ["agent_1", "agent_2"]
    assert settings.database_url.startswith("postgresql+asyncpg://")


def test_values_are_read_from_the_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("INGEST_TOKEN", "abc")
    monkeypatch.setenv("TEMPORAL_ADDRESS", "temporal:7233")
    monkeypatch.setenv("MAX_DIFF_CHARS", "10")
    monkeypatch.setenv("AGENT_NAMES", "claude, codex ,")

    settings = Settings()  # type: ignore[call-arg]

    assert settings.ingest_token == "abc"
    assert settings.temporal_address == "temporal:7233"
    assert settings.max_diff_chars == 10
    assert settings.agent_names == ["claude", "codex"]


@pytest.mark.parametrize("token", [None, ""])
def test_missing_or_empty_ingest_token_fails_fast(
    monkeypatch: pytest.MonkeyPatch, token: str | None
) -> None:
    monkeypatch.delenv("INGEST_TOKEN", raising=False)
    if token is not None:
        monkeypatch.setenv("INGEST_TOKEN", token)

    with pytest.raises(ValidationError):
        Settings()  # type: ignore[call-arg]


@pytest.mark.parametrize("value", ["0", "-5"])
def test_diff_limit_must_be_positive(monkeypatch: pytest.MonkeyPatch, value: str) -> None:
    monkeypatch.setenv("INGEST_TOKEN", "t")
    monkeypatch.setenv("MAX_DIFF_CHARS", value)

    with pytest.raises(ValidationError):
        Settings()  # type: ignore[call-arg]


def test_agent_names_cannot_be_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AGENT_NAMES", " , ")

    with pytest.raises(ValidationError):
        WorkerSettings()


def test_worker_settings_do_not_require_the_ingest_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("INGEST_TOKEN", raising=False)

    assert WorkerSettings().agent_names
