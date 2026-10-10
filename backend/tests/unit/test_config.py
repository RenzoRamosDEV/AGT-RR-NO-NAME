import pytest
from pydantic import ValidationError

from duelo.config import Settings, WorkerSettings


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


_OPERATOR = "o" * 16


def test_operator_token_is_optional_and_off_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("INGEST_TOKEN", "t")
    monkeypatch.delenv("OPERATOR_TOKEN", raising=False)

    assert Settings().operator_token is None  # type: ignore[call-arg]


@pytest.mark.parametrize("blank", ["", "   "])
def test_a_blank_operator_token_means_not_configured(
    monkeypatch: pytest.MonkeyPatch, blank: str
) -> None:
    monkeypatch.setenv("INGEST_TOKEN", "t")
    monkeypatch.setenv("OPERATOR_TOKEN", blank)

    assert Settings().operator_token is None  # type: ignore[call-arg]


def test_operator_token_is_read_from_the_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("INGEST_TOKEN", "t")
    monkeypatch.setenv("OPERATOR_TOKEN", _OPERATOR)

    assert Settings().operator_token == _OPERATOR  # type: ignore[call-arg]


@pytest.mark.parametrize(("length", "valid"), [(15, False), (16, True), (17, True)])
def test_operator_token_needs_at_least_16_characters(
    monkeypatch: pytest.MonkeyPatch, length: int, valid: bool
) -> None:
    monkeypatch.setenv("INGEST_TOKEN", "t")
    monkeypatch.setenv("OPERATOR_TOKEN", "x" * length)

    if valid:
        assert Settings().operator_token == "x" * length  # type: ignore[call-arg]
    else:
        with pytest.raises(ValidationError):
            Settings()  # type: ignore[call-arg]


def test_operator_token_must_differ_from_the_ingest_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """El token de ingesta lo llevan los hooks de los repos: no puede abrir la salida cruda."""
    monkeypatch.setenv("INGEST_TOKEN", _OPERATOR)
    monkeypatch.setenv("OPERATOR_TOKEN", _OPERATOR)

    with pytest.raises(ValidationError, match="distinto de INGEST_TOKEN"):
        Settings()  # type: ignore[call-arg]


def test_round4_defaults_are_safe(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ("ALLOWED_ORIGINS", "RATE_LIMIT_REQUESTS", "RATE_LIMIT_WINDOW_SECONDS"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.delenv("STALE_AFTER_SECONDS", raising=False)
    monkeypatch.setenv("INGEST_TOKEN", "t")

    settings = Settings()  # type: ignore[call-arg]

    assert settings.allowed_origins == []  # sin CORS salvo que se pida
    assert settings.rate_limit_requests == 300
    assert settings.rate_limit_window_seconds == 60
    assert settings.stale_after_seconds == 1800


def test_allowed_origins_are_a_comma_separated_list(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("INGEST_TOKEN", "t")
    monkeypatch.setenv("ALLOWED_ORIGINS", "http://localhost:5173, https://duelo.example.com:8443 ,")

    settings = Settings()  # type: ignore[call-arg]

    assert settings.allowed_origins == ["http://localhost:5173", "https://duelo.example.com:8443"]


@pytest.mark.parametrize(
    "origin",
    ["*", "localhost:5173", "http://localhost:5173/app", "ftp://host", "http://", "http://h?x=1"],
)
def test_allowed_origins_reject_wildcards_and_malformed_origins(
    monkeypatch: pytest.MonkeyPatch, origin: str
) -> None:
    monkeypatch.setenv("INGEST_TOKEN", "t")
    monkeypatch.setenv("ALLOWED_ORIGINS", origin)

    with pytest.raises(ValidationError):
        Settings()  # type: ignore[call-arg]


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("RATE_LIMIT_REQUESTS", "-1"),
        ("RATE_LIMIT_WINDOW_SECONDS", "0"),
        ("STALE_AFTER_SECONDS", "0"),
        ("STALE_AFTER_SECONDS", "-3"),
    ],
)
def test_round4_numbers_are_validated(
    monkeypatch: pytest.MonkeyPatch, name: str, value: str
) -> None:
    monkeypatch.setenv("INGEST_TOKEN", "t")
    monkeypatch.setenv(name, value)

    with pytest.raises(ValidationError):
        Settings()  # type: ignore[call-arg]


def test_rate_limit_can_be_disabled_with_zero(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("INGEST_TOKEN", "t")
    monkeypatch.setenv("RATE_LIMIT_REQUESTS", "0")

    assert Settings().rate_limit_requests == 0  # type: ignore[call-arg]


# --- proyectos desde carpetas locales ---------------------------------------------------------


def test_local_projects_settings_default_to_off(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in (
        "LOCAL_PROJECTS_ENABLED",
        "INGEST_URL",
        "PR_SYNC_INTERVAL_SECONDS",
        "HOOK_ENV_PATH",
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("INGEST_TOKEN", "t")

    settings = Settings()  # type: ignore[call-arg]

    assert settings.local_projects_enabled is False
    assert settings.ingest_url == "http://127.0.0.1:8000"
    assert settings.pr_sync_interval_seconds == 0  # sin sincronización periódica
    assert settings.hook_env_path is None


def test_local_projects_settings_are_read_from_the_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("INGEST_TOKEN", "t")
    monkeypatch.setenv("LOCAL_PROJECTS_ENABLED", "true")
    monkeypatch.setenv("INGEST_URL", "http://localhost:8001/")
    monkeypatch.setenv("PR_SYNC_INTERVAL_SECONDS", "300")
    monkeypatch.setenv("HOOK_ENV_PATH", "/tmp/duelo/hook.env")

    settings = Settings()  # type: ignore[call-arg]

    assert settings.local_projects_enabled is True
    assert settings.ingest_url == "http://localhost:8001"  # sin barra final
    assert settings.pr_sync_interval_seconds == 300
    assert settings.hook_env_path == "/tmp/duelo/hook.env"


@pytest.mark.parametrize("url", ["", "localhost:8000", "ftp://x", "http://", "javascript:alert(1)"])
def test_ingest_url_must_be_an_http_url_with_a_host(
    monkeypatch: pytest.MonkeyPatch, url: str
) -> None:
    monkeypatch.setenv("INGEST_TOKEN", "t")
    monkeypatch.setenv("INGEST_URL", url)

    with pytest.raises(ValidationError, match="INGEST_URL"):
        Settings()  # type: ignore[call-arg]


def test_a_negative_sync_interval_is_rejected_and_a_blank_hook_env_path_means_unset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("INGEST_TOKEN", "t")
    monkeypatch.setenv("HOOK_ENV_PATH", "  ")
    assert Settings().hook_env_path is None  # type: ignore[call-arg]

    monkeypatch.setenv("PR_SYNC_INTERVAL_SECONDS", "-1")
    with pytest.raises(ValidationError):
        Settings()  # type: ignore[call-arg]
