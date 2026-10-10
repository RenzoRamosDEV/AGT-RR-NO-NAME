"""Configuración 12-factor: todo viene del entorno y se valida al arrancar."""

from __future__ import annotations

from typing import Annotated
from urllib.parse import urlsplit

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

from duelo.application.review_timeouts import MAX_AGENT_TIMEOUT_SECONDS

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

    # Agentes reales: `claude` y `codex` en AGENT_NAMES usan los CLI de la máquina (con la sesión
    # que el usuario ya tiene iniciada, sin claves de API); otro nombre es el agente de prueba.
    # Plazo de cada ejecución. Como máximo el de la activity menos un margen de 30 s (para limpiar y
    # guardar la review fallida al vencer): `application/review_timeouts.py`.
    agent_timeout_seconds: float = Field(default=240.0, gt=0, le=MAX_AGENT_TIMEOUT_SECONDS)
    # Cuántos CLI pueden ejecutarse a la vez en este worker.
    agent_max_concurrency: int = Field(default=2, ge=1)
    # Ruta del ejecutable si no está en el PATH; vacío = buscarlo en el PATH.
    claude_bin: str | None = None
    codex_bin: str | None = None
    # Modelo opcional; vacío = el que use el CLI por defecto.
    claude_model: str | None = None
    codex_model: str | None = None
    # Tope de gasto (en USD de lista) de una sola ejecución de Claude Code.
    claude_max_budget_usd: float = Field(default=2.0, gt=0)

    @field_validator("agent_names", mode="before")
    @classmethod
    def _split_agent_names(cls, value: object) -> object:
        return _split_csv(value)

    @field_validator("agent_names")
    @classmethod
    def _at_least_one_agent(cls, value: list[str]) -> list[str]:
        if not value:
            raise ValueError("AGENT_NAMES debe tener al menos un agente")
        # Un nombre repetido (también si solo cambian las mayúsculas) es un error: el estado de un
        # change espera `len(AGENT_NAMES)` reviews, pero cada agente solo da una por run.
        seen: set[str] = set()
        for name in value:
            if name.casefold() in seen:
                raise ValueError(f"AGENT_NAMES repite el agente '{name}': cada nombre solo una vez")
            seen.add(name.casefold())
        return value

    @field_validator("claude_bin", "codex_bin", "claude_model", "codex_model", mode="before")
    @classmethod
    def _blank_is_unset(cls, value: object) -> object:
        # `CLAUDE_BIN=` en un .env significa «no configurado», no la ruta vacía.
        return None if isinstance(value, str) and not value.strip() else value


class Settings(WorkerSettings):
    # Obligatorio: sin él la API no arranca, en vez de quedar abierta por accidente.
    ingest_token: str = Field(min_length=1)
    max_diff_chars: int = Field(default=200_000, gt=0)
    # Tamaño máximo del cuerpo HTTP de POST /ingest/commit y /ingest/pr (413 si lo supera). Protege
    # la memoria y es independiente del truncado del diff: debe dejar holgura para `max_diff_chars`
    # caracteres con escapes JSON y UTF-8, y para el 1 000 000 que ya recorta el hook.
    max_ingest_body_bytes: int = Field(default=1_500_000, gt=0)
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
    # Cada cuántos segundos se comprueba qué commits de los proyectos locales siguen siendo
    # alcanzables en su repositorio (los que dejan de serlo se marcan como «deshechos»); 0 = nunca.
    # Solo corre con LOCAL_PROJECTS_ENABLED.
    reachability_sweep_interval_seconds: int = Field(default=15, ge=0)
    # Cuántos commits (los más recientes) se piden a git en cada barrido. Con un repositorio más
    # grande solo se evalúan los changes recientes y se confirma cada candidato uno a uno.
    reachability_window_commits: int = Field(default=5000, ge=1, le=100_000)

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
