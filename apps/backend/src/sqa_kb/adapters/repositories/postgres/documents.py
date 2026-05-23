"""PostgresDocumentRepository — catálogo de documentos del KB.

Implementa el contrato de `searchDocuments` que el frontend definió en
Fase 7 (lib/api/documents.ts) — los mismos filtros (carpetas, tipos,
estados, autoritativo, anonimizado, minScore, dateFrom/dateTo, autorOid),
mismo sort (relevance/date_desc/score_desc/citations_desc), misma
paginación (offset {page, limit}).
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from datetime import datetime
from typing import Any

from sqlalchemy import case, func, or_, select
from sqlalchemy.ext.asyncio import async_sessionmaker

from sqa_kb.adapters.repositories.postgres import mappers, models
from sqa_kb.adapters.repositories.postgres.session import session_scope
from sqa_kb.domain.entities import (
    CaptureScore,
    Document,
    DocumentDetail,
    MyCapturesStats,
)
from sqa_kb.domain.errors import NotFoundError, ForbiddenError
from sqa_kb.domain.value_objects import CategoryCode, DocStatus, DocTypeCode


class PostgresDocumentRepository:
    def __init__(self, session_factory) -> None:  # type: ignore[no-untyped-def]
        self._session_factory: async_sessionmaker = session_factory

    async def get(self, document_id: str) -> Document | None:
        async with self._session_factory() as session:
            model = await session.get(models.DocumentModel, document_id)
            return mappers.to_document_entity(model) if model else None

    async def get_detail(self, document_id: str) -> DocumentDetail | None:
        async with self._session_factory() as session:
            model = await session.get(models.DocumentModel, document_id)
            if model is None:
                return None
            # Incoming citations: documentos cuyos mensajes citaron a este doc.
            # En Fase 1 el grafo de citas aún no se popula desde el agente;
            # devolvemos vacío. En Fase 3 (RAG) se llena al indexar.
            return mappers.to_document_detail_entity(model, incoming_citations=[])

    async def search(  # noqa: PLR0913 — espejo del contrato frontend
        self,
        *,
        query: str | None = None,
        carpetas: Iterable[CategoryCode] | None = None,
        tipos: Iterable[DocTypeCode] | None = None,
        estados: Iterable[DocStatus] | None = None,
        autoritativo: bool | None = None,
        anonimizado: bool | None = None,
        min_score: float | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        author_oid: str | None = None,
        sort_by: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[Sequence[Document], int]:
        async with self._session_factory() as session:
            base = select(models.DocumentModel)

            # Filtros estructurados ---
            if carpetas:
                base = base.where(
                    models.DocumentModel.carpeta.in_([str(c) for c in carpetas])
                )
            if tipos:
                base = base.where(
                    models.DocumentModel.tipo.in_([str(t) for t in tipos])
                )
            if estados:
                base = base.where(
                    models.DocumentModel.estado.in_([str(e) for e in estados])
                )
            if autoritativo is not None:
                base = base.where(models.DocumentModel.autoritativo == autoritativo)
            if anonimizado is not None:
                base = base.where(models.DocumentModel.anonimizado == anonimizado)
            if min_score is not None:
                base = base.where(models.DocumentModel.score >= min_score)
            if date_from is not None:
                # ISO date string (YYYY-MM-DD) — Postgres lo compara con la
                # columna timestamp tras cast implícito.
                base = base.where(
                    models.DocumentModel.fecha >= datetime.fromisoformat(date_from)
                )
            if date_to is not None:
                base = base.where(
                    models.DocumentModel.fecha <= datetime.fromisoformat(date_to)
                )
            if author_oid is not None:
                base = base.where(models.DocumentModel.autor_oid == author_oid)

            # Búsqueda textual ---
            # Fase 1 = ILIKE simple sobre título + autor. En Fase 3 esto se
            # reemplaza por hybrid search (tsvector + pgvector) sin tocar
            # el contrato de este método.
            if query and query.strip():
                needle = f"%{query.strip().lower()}%"
                base = base.where(
                    or_(
                        func.lower(models.DocumentModel.titulo).like(needle),
                        func.lower(models.DocumentModel.autor_name).like(needle),
                    )
                )

            # Total para paginación ANTES de aplicar limit/offset.
            count_stmt = select(func.count()).select_from(base.subquery())
            total: int = (await session.execute(count_stmt)).scalar_one()

            # Ordenamiento ---
            effective_sort = sort_by or (
                "relevance" if query and query.strip() else "date_desc"
            )
            base = self._apply_sort(base, effective_sort)

            # Paginación ---
            base = base.limit(max(1, limit)).offset(max(0, offset))
            rows = (await session.execute(base)).scalars().all()
            items = [mappers.to_document_entity(r) for r in rows]
            return items, total

    def _apply_sort(self, stmt, sort_by: str):  # type: ignore[no-untyped-def]
        d = models.DocumentModel
        match sort_by:
            case "date_desc":
                return stmt.order_by(d.fecha.desc())
            case "score_desc":
                return stmt.order_by(d.score.desc())
            case "citations_desc":
                return stmt.order_by(d.citas.desc())
            case "relevance":
                # Mismo formula que el stub del frontend (Fase 7.1):
                # score*0.6 + min(citas, 60)*0.04.
                citas_capped = case(
                    (d.citas > 60, 60), else_=d.citas
                )
                rel = d.score * 0.6 + citas_capped * 0.04
                return stmt.order_by(rel.desc())
            case _:
                return stmt.order_by(d.fecha.desc())

    async def create(self, doc: Document) -> Document:
        async with session_scope(self._session_factory) as session:
            model = mappers.new_document_model(doc)
            session.add(model)
            await session.flush()
            await session.refresh(model)
            return mappers.to_document_entity(model)

    async def update(self, doc: Document) -> Document:
        async with session_scope(self._session_factory) as session:
            model = await session.get(models.DocumentModel, doc.id)
            if model is None:
                raise NotFoundError(f"Documento {doc.id} no encontrado")
            # Aplica todos los campos editables; los timestamps los maneja la BD.
            for field, value in {
                "titulo": doc.titulo,
                "carpeta": str(doc.carpeta),
                "tipo": str(doc.tipo),
                "autoritativo": doc.autoritativo,
                "estado": str(doc.estado),
                "autor_name": doc.autor_name,
                "autor_role": doc.autor_role,
                "revision": doc.revision,
                "version": doc.version,
                "citas": doc.citas,
                "score": doc.score,
                "anonimizado": doc.anonimizado,
                "fragmentos": doc.fragmentos,
                "paginas": doc.paginas,
                "formato": doc.formato,
                "aprobador_name": doc.aprobador_name,
                "fecha_aprobacion": doc.fecha_aprobacion,
                "tags": list(doc.tags),
                "blob_path": doc.blob_path,
            }.items():
                setattr(model, field, value)
            await session.flush()
            await session.refresh(model)
            return mappers.to_document_entity(model)

    async def set_authoritative(
        self,
        document_id: str,
        *,
        value: bool,
        caller_oid: str,
    ) -> Document:
        """Cambia el flag autoritativo. Solo Owner sobre su carpeta o GK Lead.
        El enforcement del rol queda en services — acá solo verificamos que
        el doc exista y persistimos."""
        async with session_scope(self._session_factory) as session:
            model = await session.get(models.DocumentModel, document_id)
            if model is None:
                raise NotFoundError(f"Documento {document_id} no encontrado")
            # caller_oid se usa en services para checks de carpetas_owned;
            # acá lo aceptamos para que el contrato del port se mantenga.
            del caller_oid
            model.autoritativo = value
            await session.flush()
            await session.refresh(model)
            return mappers.to_document_entity(model)

    async def list_by_author(
        self,
        author_oid: str,
        *,
        limit: int = 200,
    ) -> tuple[Sequence[Document], MyCapturesStats]:
        async with self._session_factory() as session:
            result = await session.execute(
                select(models.DocumentModel)
                .where(models.DocumentModel.autor_oid == author_oid)
                .order_by(models.DocumentModel.fecha.desc())
                .limit(limit)
            )
            rows = result.scalars().all()
            items = [mappers.to_document_entity(r) for r in rows]

            stats = self._compute_my_stats(rows)
            return items, stats

    def _compute_my_stats(
        self, rows: Sequence[models.DocumentModel]
    ) -> MyCapturesStats:
        if not rows:
            return MyCapturesStats()
        total = len(rows)
        citas_total = sum(r.citas for r in rows)
        avg_score = round(sum(r.score for r in rows) / total, 2)
        last_captured_at: datetime | None = max(r.fecha for r in rows)
        return MyCapturesStats(
            total_captures=total,
            total_citations_received=citas_total,
            avg_score=avg_score,
            last_captured_at=last_captured_at,
        )

    async def save_score(self, score: CaptureScore) -> CaptureScore:
        async with session_scope(self._session_factory) as session:
            existing = await session.get(models.CaptureScoreModel, score.document_id)
            if existing is None:
                session.add(
                    models.CaptureScoreModel(
                        document_id=score.document_id,
                        specificity=score.specificity,
                        depth=score.depth,
                        reusability=score.reusability,
                        uniqueness=score.uniqueness,
                        value_score=score.value_score,
                        computed_at=score.computed_at,
                    )
                )
            else:
                existing.specificity = score.specificity
                existing.depth = score.depth
                existing.reusability = score.reusability
                existing.uniqueness = score.uniqueness
                existing.value_score = score.value_score
                existing.computed_at = score.computed_at
            return score


# Reservado para future-proofing — re-export del error correcto al
# top-level del módulo facilita el patch en tests.
_ = ForbiddenError, Any
