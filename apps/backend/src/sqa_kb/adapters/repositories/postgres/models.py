"""SQLAlchemy 2.0 ORM models — mapping a las entidades del dominio.

Cada model corresponde a una tabla. Los nombres de tabla y columna están
en `snake_case`; los nombres Python siguen el dominio Pydantic.

Reglas:
- IDs UUID4 como `String(36)` (no PostgreSQL UUID type para que migrar a
  Azure SQL después solo cambie el dialect, no los tipos).
- Timestamps como `DateTime(timezone=True)` (TIMESTAMPTZ en postgres).
- Listas y dicts arbitrarios como `JSONB`. Pgvector para vectores.
- Constraint de unicidad y foreign keys explícitos para que Alembic los
  detecte en autogenerate.

`MappedAsDataclass` hace que los models tengan `__init__` con keyword args.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from sqa_kb.adapters.repositories.postgres.base import Base


# ===========================================================================
# Identidad
# ===========================================================================


class UserModel(Base):
    __tablename__ = "users"

    oid: Mapped[str] = mapped_column(String(128), primary_key=True)
    email: Mapped[str] = mapped_column(String(320), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    role_id: Mapped[str] = mapped_column(String(16), nullable=False)
    carpetas_owned: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, default=list
    )
    puede_gobernar_taxonomia: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    puede_aprobar_taxonomia: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    puede_ver_metricas_globales: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


# ===========================================================================
# Taxonomía (catálogos)
# ===========================================================================


class CategoryModel(Base):
    __tablename__ = "categories"

    code: Mapped[str] = mapped_column(String(8), primary_key=True)
    label: Mapped[str] = mapped_column(String(64), nullable=False)
    docs: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    vigentes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    autoritativos: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    score_avg: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    obsolescencia: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class DocTypeModel(Base):
    __tablename__ = "doc_types"

    code: Mapped[str] = mapped_column(String(8), primary_key=True)
    label: Mapped[str] = mapped_column(String(64), nullable=False)


# ===========================================================================
# Documentos del KB
# ===========================================================================


class DocumentModel(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    titulo: Mapped[str] = mapped_column(String(500), nullable=False)
    carpeta: Mapped[str] = mapped_column(
        String(8), ForeignKey("categories.code"), nullable=False, index=True
    )
    tipo: Mapped[str] = mapped_column(
        String(8), ForeignKey("doc_types.code"), nullable=False, index=True
    )
    autoritativo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    estado: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    autor_oid: Mapped[str | None] = mapped_column(
        String(128), ForeignKey("users.oid"), nullable=True, index=True
    )
    autor_name: Mapped[str] = mapped_column(String(255), nullable=False)
    autor_role: Mapped[str] = mapped_column(String(64), nullable=False)
    fecha: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revision: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    version: Mapped[str] = mapped_column(String(16), nullable=False)
    citas: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    anonimizado: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    fragmentos: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    paginas: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    formato: Mapped[str] = mapped_column(String(16), nullable=False)
    aprobador_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    fecha_aprobacion: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    tags: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    blob_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    resumen: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    __table_args__ = (
        Index("ix_documents_fecha_desc", fecha.desc()),
        Index("ix_documents_score_desc", score.desc()),
    )


class CaptureScoreModel(Base):
    __tablename__ = "capture_scores"

    document_id: Mapped[str] = mapped_column(
        String(128), ForeignKey("documents.id", ondelete="CASCADE"), primary_key=True
    )
    specificity: Mapped[float] = mapped_column(Float, nullable=False)
    depth: Mapped[float] = mapped_column(Float, nullable=False)
    reusability: Mapped[float] = mapped_column(Float, nullable=False)
    uniqueness: Mapped[float] = mapped_column(Float, nullable=False)
    value_score: Mapped[float] = mapped_column(Float, nullable=False)
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )


class DocumentChunkModel(Base):
    """Chunk vectorial — usado por RAG (Fase 3). Schema listo desde 1B.1."""

    __tablename__ = "document_chunks"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    document_id: Mapped[str] = mapped_column(
        String(128),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(1024), nullable=True)
    """1024-dim por Cohere multilingual-v3 (decisión de ROADMAP §11.3).
    Si TI elige Azure AI Search, este campo se ignora (chunks viven allá)."""

    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSONB, nullable=False, default=dict
    )

    __table_args__ = (
        UniqueConstraint("document_id", "chunk_index", name="uq_chunk_doc_idx"),
    )


# ===========================================================================
# Sesiones y mensajes (chat con Aria)
# ===========================================================================


class SessionModel(Base):
    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    owner_oid: Mapped[str] = mapped_column(
        String(128), ForeignKey("users.oid"), nullable=False, index=True
    )
    mode: Mapped[str] = mapped_column(String(16), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    current_stage: Mapped[str | None] = mapped_column(String(4), nullable=True)
    message_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    agent_state: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        comment="LangGraph state checkpointer — Fase 2",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    messages: Mapped[list["MessageModel"]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="MessageModel.started_at",
    )


class MessageModel(Base):
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    session_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False, default="")
    stage: Mapped[str | None] = mapped_column(String(4), nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    ended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Payloads serializados como JSONB — los models Pydantic los reconstruyen
    # del lado del repository. Mantenemos schema flexible para no requerir
    # migration cada vez que cambie un payload menor.
    classification: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    citations: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, nullable=False, default=list
    )
    scoring: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    artifacts: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, nullable=False, default=list
    )
    token_usage: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    cost_usd: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    """Denormalizado de token_usage para queries de cost reporting más rápidas."""
    error_payload: Mapped[str | None] = mapped_column(Text, nullable=True)

    session: Mapped["SessionModel"] = relationship(back_populates="messages")


# ===========================================================================
# Ingesta + Queries + Skills + Audit
# ===========================================================================


class IngestionItemModel(Base):
    __tablename__ = "ingestion_items"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    filename: Mapped[str] = mapped_column(String(500), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    paginas: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    carpeta_sugerida: Mapped[str | None] = mapped_column(String(8), nullable=True)
    tipo_sugerido: Mapped[str | None] = mapped_column(String(8), nullable=True)
    aprobador_oid: Mapped[str | None] = mapped_column(String(128), nullable=True)
    aprobador_name: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    fecha_aprobacion: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    fuente_original: Mapped[str] = mapped_column(String(1024), nullable=False, default="")
    version: Mapped[str] = mapped_column(String(16), nullable=False, default="")
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    uploaded_by_oid: Mapped[str] = mapped_column(
        String(128), ForeignKey("users.oid"), nullable=False
    )
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    blob_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    error_detail: Mapped[str | None] = mapped_column(Text, nullable=True)


class QueryModel(Base):
    __tablename__ = "queries"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_oid: Mapped[str] = mapped_column(
        String(128), ForeignKey("users.oid"), nullable=False, index=True
    )
    session_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("sessions.id", ondelete="SET NULL"), nullable=True
    )
    text: Mapped[str] = mapped_column(Text, nullable=False)
    asked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    answered_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    has_result: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class QueryCitationModel(Base):
    __tablename__ = "query_citations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    query_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("queries.id", ondelete="CASCADE"), nullable=False, index=True
    )
    document_id: Mapped[str] = mapped_column(
        String(128), ForeignKey("documents.id"), nullable=False, index=True
    )
    section: Mapped[str] = mapped_column(String(255), nullable=False)
    snippet: Mapped[str] = mapped_column(Text, nullable=False)


class SkillModel(Base):
    __tablename__ = "skills"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    body_markdown: Mapped[str] = mapped_column(Text, nullable=False, default="")
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    updated_by_oid: Mapped[str | None] = mapped_column(String(128), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class AuditLogModel(Base):
    __tablename__ = "audit_log"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    actor_oid: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    resource_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    audit_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSONB, nullable=False, default=dict
    )
    at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )


# ===========================================================================
# Dashboard helpers (denormalized — alimentados por workers en Fase 3)
# ===========================================================================


class HotTopicModel(Base):
    """Snapshot del top de temas en demanda. Refrescado periódicamente."""

    __tablename__ = "hot_topics_snapshot"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    topic: Mapped[str] = mapped_column(String(255), nullable=False)
    queries_30d: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    citation_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_gap: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class RecentActivityModel(Base):
    """Append-only feed. Las queries del dashboard usan `ORDER BY at DESC LIMIT N`."""

    __tablename__ = "recent_activity"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    type: Mapped[str] = mapped_column(String(32), nullable=False)
    actor_oid: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    actor_name: Mapped[str] = mapped_column(String(255), nullable=False)
    at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    summary: Mapped[str] = mapped_column(String(500), nullable=False)
    ref_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)


# Para que Alembic detecte todos los models por importación lateral.
__all__ = [
    "AuditLogModel",
    "CaptureScoreModel",
    "CategoryModel",
    "DocTypeModel",
    "DocumentChunkModel",
    "DocumentModel",
    "HotTopicModel",
    "IngestionItemModel",
    "MessageModel",
    "QueryCitationModel",
    "QueryModel",
    "RecentActivityModel",
    "SessionModel",
    "SkillModel",
    "UserModel",
]


# Suppressing unused import warning from JSON — necesario para que el binding
# del dialect funcione en builds futuros sobre Azure SQL (que no soporta JSONB).
_ = JSON
