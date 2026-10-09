"""Configuración 12-factor: todo viene del entorno y se valida al arrancar."""

from __future__ import annotations

from typing import Annotated
from urllib.parse import urlsplit

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

MIN_OPERATOR_TOKEN = 16


def _split_csv(value: object) -> object:
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    return value


class WorkerSettings(BaseSettings):
    """Lo que necesita cualquier proceso que habla con Postgres y Temporal (el worker)."""

    model_config = SettingsConfigDict(case_sensitive=False, extra="ignore")

    database_url: str = "postgresql+asyncpg://duelo:duelo@localhost:5432/duelo"
    temporal_address: str = "localhost:7233"
    # Lista separada por comas en el entorno: AGENT_NAMES=agent_1,agent_2
    agent_names: Annotated[list[str], NoDecode] = ["agent_1", "agent_2"]

    @field_validator("agent_names", mode="before")
    @classmethod
    def _split_agent_names(cls, value: object) -> object:
        return _split_csv(value)

    @field_validator("agent_names")
    @classmethod
    def _at_least_one_agent(cls, value: list[str]) -> list[str]:
        if not value:
            raise ValueError("AGENT_NAMES debe tener al menos un agente")
        return value


class Settings(WorkerSettings):
    # Obligatorio: sin él la API no arranca, en vez de quedar abierta por accidente.
    ingest_token: str = Field(min_length=1)
    max_diff_chars: int = Field(default=200_000, gt=0)
    # Opcional: sin él, `GET /reviews/{id}/raw-output` queda deshabilitado (404). Es un secreto
    # distinto del de ingesta: ese lo llevan los hooks de los repos y no debe abrir lecturas.
    operator_token: str | None = Field(default=None, min_length=MIN_OPERATOR_TOKEN)

    # Orígenes que pueden llamar a la API desde un navegador: ALLOWED_ORIGINS=http://localhost:5173.
    # Vacía (por defecto) = sin CORS.
    allowed_origins: Annotated[list[str], NoDecode] = []
    # Ventana deslizante por IP para POST /ingest/* y /changes/{id}/retry; 0 = sin límite.
    rate_limit_requests: int = Field(default=300, ge=0)
    rate_limit_window_seconds: int = Field(default=60, gt=0)
    # Un change pending/running más antiguo que esto se marca `stale` (solo diagnóstico).
    stale_after_seconds: int = Field(default=1800, gt=0)

    # Altas de proyectos desde carpetas locales (instala hooks de git): apagado por defecto y solo
    # con la API corriendo en la máquina del usuario. Sin activar, esos endpoints dan 404.
    local_projects_enabled: bool = False
    # Base de la API que usan los hooks de git para enviar commits (el backend no sabe en qué
    # puerto lo lanzó uvicorn).
    ingest_url: str = "http://127.0.0.1:8000"
    # Fichero con INGEST_URL e INGEST_TOKEN que leen los hooks; por defecto
    # ~/.config/duelo/hook.env (o $XDG_CONFIG_HOME/duelo/hook.env).
    hook_env_path: str | None = None
    # Cada cuántos segundos se sincronizan las PRs de los proyectos locales con `gh`; 0 = nunca.
    pr_sync_interval_seconds: int = Field(default=0, ge=0)

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def _split_allowed_origins(cls, value: object) -> object:
        return _split_csv(value)

    @field_validator("allowed_origins")
    @classmethod
    def _origins_are_explicit(cls, value: list[str]) -> list[str]:
        for origin in value:
            parts = urlsplit(origin)
            valid = (
                parts.scheme in {"http", "https"}
                and bool(parts.netloc)
                and parts.path == ""
                and not (parts.query or parts.fragment)
            )
            if not valid:
                raise ValueError(
                    f"ALLOWED_ORIGINS solo admite orígenes esquema://host[:puerto] (sin '*' ni "
                    f"ruta): {origin!r}"
                )
        return value

    @field_validator("ingest_url")
    @classmethod
    def _ingest_url_is_http(cls, value: str) -> str:
        parts = urlsplit(value)
        if parts.scheme not in {"http", "https"} or not parts.netloc:
            raise ValueError(f"INGEST_URL debe ser una URL http(s) con host: {value!r}")
        return value.rstrip("/")

    @field_validator("hook_env_path", mode="before")
    @classmethod
    def _blank_hook_env_path_is_unset(cls, value: object) -> object:
        return None if isinstance(value, str) and not value.strip() else value

    @field_validator("operator_token", mode="before")
    @classmethod
    def _blank_operator_token_is_unset(cls, value: object) -> object:
        # `OPERATOR_TOKEN=` en un compose o .env significa "sin configurar", no un token vacío.
        return None if isinstance(value, str) and not value.strip() else value

    @model_validator(mode="after")
    def _operator_token_differs_from_ingest_token(self) -> Settings:
        if self.operator_token is not None and self.operator_token == self.ingest_token:
            raise ValueError("OPERATOR_TOKEN debe ser distinto de INGEST_TOKEN")
        return self
