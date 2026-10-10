import pytest
from pydantic import ValidationError

from duelo.config import MAX_AGENT_TIMEOUT_SECONDS, Settings, WorkerSettings


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


_AGENT_VARIABLES = (
    "AGENT_TIMEOUT_SECONDS",
    "AGENT_MAX_CONCURRENCY",
    "CLAUDE_BIN",
    "CODEX_BIN",
    "CLAUDE_MODEL",
    "CODEX_MODEL",
    "CLAUDE_MAX_BUDGET_USD",
)


def test_cli_agent_defaults_need_no_configuration_and_no_api_keys(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for name in _AGENT_VARIABLES:
        monkeypatch.delenv(name, raising=False)

    settings = WorkerSettings()

    assert settings.agent_timeout_seconds == 240
    assert settings.agent_max_concurrency == 2
    assert (settings.claude_bin, settings.codex_bin) == (None, None)
    assert (settings.claude_model, settings.codex_model) == (None, None)
    assert settings.claude_max_budget_usd == 2.0
    assert not any("api_key" in field for field in WorkerSettings.model_fields)


def test_cli_agent_settings_are_read_from_the_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AGENT_TIMEOUT_SECONDS", "90.5")
    monkeypatch.setenv("AGENT_MAX_CONCURRENCY", "4")
    monkeypatch.setenv("CLAUDE_BIN", "/opt/claude")
    monkeypatch.setenv("CODEX_BIN", "/opt/codex")
    monkeypatch.setenv("CLAUDE_MODEL", "opus")
    monkeypatch.setenv("CODEX_MODEL", "gpt-x")
    monkeypatch.setenv("CLAUDE_MAX_BUDGET_USD", "0.75")

    settings = WorkerSettings()

    assert settings.agent_timeout_seconds == 90.5
    assert settings.agent_max_concurrency == 4
    assert (settings.claude_bin, settings.codex_bin) == ("/opt/claude", "/opt/codex")
    assert (settings.claude_model, settings.codex_model) == ("opus", "gpt-x")
    assert settings.claude_max_budget_usd == 0.75


@pytest.mark.parametrize("blank", ["", "   "])
def test_a_blank_binary_or_model_means_not_configured(
    monkeypatch: pytest.MonkeyPatch, blank: str
) -> None:
    for name in ("CLAUDE_BIN", "CODEX_BIN", "CLAUDE_MODEL", "CODEX_MODEL"):
        monkeypatch.setenv(name, blank)

    settings = WorkerSettings()

    assert (settings.claude_bin, settings.codex_bin) == (None, None)
    assert (settings.claude_model, settings.codex_model) == (None, None)


@pytest.mark.regression
@pytest.mark.parametrize("value", ["0", "-1", "270.1", "299.9", "300", "301"])
def test_the_agent_timeout_must_leave_a_margin_below_the_activity_timeout(
    monkeypatch: pytest.MonkeyPatch, value: str
) -> None:
    """Origen: se admitía hasta 299,9 s con una activity de 300 s: al vencer el CLI no quedaba
    tiempo para limpiar y persistir la `Review(failed)`."""
    monkeypatch.setenv("AGENT_TIMEOUT_SECONDS", value)

    with pytest.raises(ValidationError):
        WorkerSettings()


@pytest.mark.parametrize("value", ["1", "240", "269.9", "270"])
def test_timeouts_up_to_the_ceiling_are_accepted(
    monkeypatch: pytest.MonkeyPatch, value: str
) -> None:
    monkeypatch.setenv("AGENT_TIMEOUT_SECONDS", value)

    assert WorkerSettings().agent_timeout_seconds == float(value)


def test_the_workflow_and_the_configuration_use_the_same_timeout_constants() -> None:
    """Si alguien cambia el plazo de la activity en un sitio y no en el otro, esto lo detecta."""
    from duelo import config
    from duelo.application import review_timeouts
    from duelo.workflows import review_change

    assert review_change.RUN_REVIEW_START_TO_CLOSE is review_timeouts.RUN_REVIEW_START_TO_CLOSE
    assert config.MAX_AGENT_TIMEOUT_SECONDS == review_timeouts.MAX_AGENT_TIMEOUT_SECONDS


def test_the_default_timeout_leaves_the_margin() -> None:
    assert WorkerSettings.model_fields["agent_timeout_seconds"].default <= MAX_AGENT_TIMEOUT_SECONDS


@pytest.mark.parametrize("name", ["AGENT_MAX_CONCURRENCY", "CLAUDE_MAX_BUDGET_USD"])
@pytest.mark.parametrize("value", ["0", "-2"])
def test_concurrency_and_budget_must_be_positive(
    monkeypatch: pytest.MonkeyPatch, name: str, value: str
) -> None:
    monkeypatch.setenv(name, value)

    with pytest.raises(ValidationError):
        WorkerSettings()


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


def test_the_ingest_body_limit_defaults_to_1_5_mb_and_is_configurable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("INGEST_TOKEN", "t")
    monkeypatch.delenv("MAX_INGEST_BODY_BYTES", raising=False)
    assert Settings().max_ingest_body_bytes == 1_500_000  # type: ignore[call-arg]

    monkeypatch.setenv("MAX_INGEST_BODY_BYTES", "4096")
    assert Settings().max_ingest_body_bytes == 4096  # type: ignore[call-arg]


@pytest.mark.parametrize("value", ["0", "-1"])
def test_the_ingest_body_limit_must_be_positive(
    monkeypatch: pytest.MonkeyPatch, value: str
) -> None:
    monkeypatch.setenv("INGEST_TOKEN", "t")
    monkeypatch.setenv("MAX_INGEST_BODY_BYTES", value)

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
