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
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class ProjectModel(Base):
    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    slug: Mapped[str] = mapped_column(String(255), unique=True)
    # Solo los proyectos dados de alta desde una carpeta local: ruta del repo y estado de sus hooks.
    path: Mapped[str | None] = mapped_column(String(4096), unique=True, nullable=True)
    hooks_installed: Mapped[bool] = mapped_column(
        Boolean(), default=False, server_default=text("false")
    )
    github: Mapped[bool] = mapped_column(Boolean(), default=False, server_default=text("false"))


class ChangeModel(Base):
    __tablename__ = "changes"
    __table_args__ = (
        UniqueConstraint("project_id", "kind", "head_sha", name="uq_changes_natural_key"),
        # Canal: orden (created_at, id) por proyecto, con y sin filtro por tipo.
        Index("ix_changes_project_created_at_id", "project_id", "created_at", "id"),
        Index("ix_changes_project_kind_created_at_id", "project_id", "kind", "created_at", "id"),
        # «¿Hay un revert vivo de este commit?»: el canal lo pregunta por cada fila. Solo los
        # commits de revert (muy pocos) entran en este índice parcial.
        Index(
            "ix_changes_project_reverts_sha",
            "project_id",
            "reverts_sha",
            postgresql_where=text("reverts_sha IS NOT NULL"),
        ),
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
    # Inicio del `run` actual (= created_at en el primero); `stale` se mide desde aquí.
    run_started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    # Resumen del diff (archivos y líneas) calculado al ingerir: el canal lo lee sin cargar `diff`.
    diff_summary: Mapped[dict[str, object]] = mapped_column(
        JSONB(),
        server_default=text(
            """'{"files_changed": 0, "additions": 0, "deletions": 0, "files": []}'::jsonb"""
        ),
    )
    # Solo commits. Cuándo el barrido de alcanzabilidad vio que el commit ya no estaba en el repo
    # local (`NULL` = alcanzable o sin evaluar); no se borra nada, solo se marca.
    discarded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Solo commits. El SHA que este commit revierte con `git revert` (`This reverts commit <sha>`),
    # o `NULL`. Un commit está revertido mientras algún commit vivo (no deshecho) apunte a su SHA.
    reverts_sha: Mapped[str | None] = mapped_column(String(64), nullable=True)


class EventModel(Base):
    __tablename__ = "events"
    __table_args__ = (
        # `GET /changes/{id}/events` busca por el change dentro del payload.
        Index("ix_events_change_id", text("(payload ->> 'change_id')")),
    )

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
        # Contadores por change y run (index-only) y lecturas por change.
        Index("ix_reviews_change_run_status", "change_id", "run", "status"),
        # Borrar un change anula `reused_from_change_id` en las reviews que copiaron de él.
        Index(
            "ix_reviews_reused_from_change_id",
            "reused_from_change_id",
            postgresql_where=text("reused_from_change_id IS NOT NULL"),
        ),
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
    # Change del que se copió la review (PR con las de su commit idéntico); `NULL` si es propia.
    reused_from_change_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("changes.id", ondelete="SET NULL"), nullable=True
    )
