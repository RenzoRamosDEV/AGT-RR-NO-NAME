"""Resolución de la URL de base de datos (12-factor: DATABASE_URL manda)."""

from duelo.adapters.persistence.db import create_engine, get_database_url

DEFAULT_URL = "postgresql+asyncpg://duelo:duelo@localhost:5432/duelo"


def test_database_url_defaults_to_the_local_docker_compose_postgres(monkeypatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)

    assert get_database_url() == DEFAULT_URL


def test_database_url_environment_variable_takes_precedence(monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@otro-host:5433/otra")

    assert get_database_url() == "postgresql+asyncpg://u:p@otro-host:5433/otra"


def test_create_engine_uses_the_environment_when_no_url_is_given(monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@host-env:5433/db")

    engine = create_engine()

    assert engine.url.host == "host-env" and engine.url.port == 5433


def test_create_engine_prefers_an_explicit_url_over_the_environment(monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@host-env:5433/db")

    engine = create_engine("postgresql+asyncpg://u:p@host-explicito:5434/db")

    assert engine.url.host == "host-explicito"
