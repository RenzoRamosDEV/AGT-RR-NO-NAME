from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class ProjectModel(Base):
    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    slug: Mapped[str] = mapped_column(String(255), unique=True)


class ChangeModel(Base):
    __tablename__ = "changes"
    __table_args__ = (
        UniqueConstraint("project_id", "kind", "head_sha", name="uq_changes_natural_key"),
        Index("ix_changes_project_created_at", "project_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE")
    )
    kind: Mapped[str] = mapped_column(String(20))
    ref: Mapped[str] = mapped_column(String(255))
    head_sha: Mapped[str] = mapped_column(String(64))
    title: Mapped[str] = mapped_column(String(500))
    author: Mapped[str] = mapped_column(String(255))
    url: Mapped[str] = mapped_column(String(1000))
    diff: Mapped[str] = mapped_column(Text())
    diff_truncated: Mapped[bool] = mapped_column(Boolean(), default=False)
    status: Mapped[str] = mapped_column(String(20))
    run: Mapped[int] = mapped_column(Integer(), default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class EventModel(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(BigInteger(), primary_key=True, autoincrement=True)
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE")
    )
    type: Mapped[str] = mapped_column(String(100))
    payload: Mapped[dict[str, object]] = mapped_column(JSONB())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ReviewModel(Base):
    __tablename__ = "reviews"
    __table_args__ = (
        UniqueConstraint("change_id", "agent", "run", name="uq_reviews_natural_key"),
        Index("ix_reviews_change_id", "change_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    change_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("changes.id", ondelete="CASCADE")
    )
    agent: Mapped[str] = mapped_column(String(50))
    run: Mapped[int] = mapped_column(Integer(), default=1)
    status: Mapped[str] = mapped_column(String(20))
    summary: Mapped[str | None] = mapped_column(Text(), nullable=True)
    score: Mapped[int | None] = mapped_column(Integer(), nullable=True)
    findings: Mapped[list[dict[str, object]]] = mapped_column(JSONB(), default=list)
    raw_output: Mapped[str | None] = mapped_column(Text(), nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer(), nullable=True)
    error: Mapped[str | None] = mapped_column(Text(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
