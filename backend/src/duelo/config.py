"""Configuración 12-factor: todo viene del entorno y se valida al arrancar."""

from __future__ import annotations

from typing import Annotated

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

MIN_OPERATOR_TOKEN = 16


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
        if isinstance(value, str):
            return [name.strip() for name in value.split(",") if name.strip()]
        return value

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
