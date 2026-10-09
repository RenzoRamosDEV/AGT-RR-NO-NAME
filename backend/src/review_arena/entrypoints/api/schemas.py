from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from review_arena.application.ingest_commit import CommitSubmission
from review_arena.domain.change import MAX_HEAD_SHA, MAX_REF, MAX_URL


class IngestCommitRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project: str = Field(min_length=1, max_length=255)
    ref: str = Field(min_length=1, max_length=MAX_REF)
    head_sha: str = Field(min_length=1, max_length=MAX_HEAD_SHA)
    title: str = ""
    author: str = ""
    url: str = Field(default="", max_length=MAX_URL)
    diff: str = ""

    @field_validator("project")
    @classmethod
    def _project_has_no_nul(cls, value: str) -> str:
        # Postgres no admite NUL en texto: sin esto la consulta del slug acabaría en un 500.
        if "\x00" in value:
            raise ValueError("project no puede contener caracteres NUL")
        return value

    def to_submission(self) -> CommitSubmission:
        return CommitSubmission(**self.model_dump())


class IngestCommitResponse(BaseModel):
    change_id: UUID
    diff_truncated: bool


class ErrorResponse(BaseModel):
    detail: str
