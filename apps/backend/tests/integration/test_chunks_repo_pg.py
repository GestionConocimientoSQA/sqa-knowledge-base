"""Tests de integración de PostgresChunkRepository (Fase 3.2).

Requiere PG real con la migración Alembic aplicada (tabla
`document_chunks` con columna `embedding vector(1024)`).
"""

from __future__ import annotations

import uuid

import pytest

from sqa_kb.adapters.repositories.postgres import models
from sqa_kb.adapters.repositories.postgres.chunks import PostgresChunkRepository
from sqa_kb.adapters.repositories.postgres.mappers import GK_GENERAL_PROJECT_ID
from sqa_kb.adapters.repositories.postgres.session import session_scope
from sqa_kb.domain.entities import DocumentChunk

# ===========================================================================
# Helpers
# ===========================================================================


def _vector(seed: float = 0.1) -> list[float]:
    """Vector 1024-dim determinista para los tests."""
    return [seed] * 1024


async def _create_test_document(session_factory, doc_id: str) -> None:  # type: ignore[no-untyped-def]
    """Doc mínimo para que el FK del chunk no falle."""
    from datetime import UTC, datetime

    async with session_scope(session_factory) as db:
        db.add(
            models.DocumentModel(
                id=doc_id,
                project_id=GK_GENERAL_PROJECT_ID,
                titulo="Doc test",
                carpeta="TEC",
                tipo="POL",
                autoritativo=False,
                estado="vigente",
                autor_oid=None,
                autor_name="A",
                autor_role="QA",
                fecha=datetime.now(UTC),
                revision=datetime.now(UTC),
                version="1.0",
                citas=0,
                score=0.0,
                anonimizado=False,
                fragmentos=0,
                paginas=1,
                formato="MD",
                tags=[],
                resumen="",
            )
        )


def _chunk(
    doc_id: str, idx: int, *, content: str = "contenido", vector: list[float] | None = None
) -> DocumentChunk:
    return DocumentChunk(
        id=f"chk-{doc_id}-{idx:04d}-{uuid.uuid4().hex[:8]}",
        document_id=doc_id,
        chunk_index=idx,
        content=content,
        embedding=vector if vector is not None else _vector(0.1 + idx * 0.01),
        metadata={"strategy": "semantic", "token_count": 50},
    )


# ===========================================================================
# bulk_insert
# ===========================================================================


async def test_bulk_insert_persists_chunks(session_factory) -> None:  # type: ignore[no-untyped-def]
    suffix = uuid.uuid4().hex[:6]
    doc_id = f"POL-bulk-{suffix}-2026-05-23"
    await _create_test_document(session_factory, doc_id)

    repo = PostgresChunkRepository(session_factory)
    chunks = [_chunk(doc_id, i) for i in range(3)]

    inserted = await repo.bulk_insert(chunks)
    assert inserted == 3

    count = await repo.count_for_document(doc_id)
    assert count == 3


async def test_bulk_insert_empty_returns_zero(session_factory) -> None:  # type: ignore[no-untyped-def]
    repo = PostgresChunkRepository(session_factory)
    assert await repo.bulk_insert([]) == 0


async def test_bulk_insert_upserts_on_conflict(session_factory) -> None:  # type: ignore[no-untyped-def]
    """Si el (document_id, chunk_index) ya existe, ON CONFLICT UPDATE."""
    suffix = uuid.uuid4().hex[:6]
    doc_id = f"POL-upsert-{suffix}-2026-05-23"
    await _create_test_document(session_factory, doc_id)

    repo = PostgresChunkRepository(session_factory)

    # Primer insert.
    original = _chunk(doc_id, 0, content="original")
    await repo.bulk_insert([original])

    # Segundo insert con mismo chunk_index pero contenido nuevo.
    updated = DocumentChunk(
        id=original.id,  # mismo ID lógico
        document_id=doc_id,
        chunk_index=0,  # mismo índice
        content="actualizado",
        embedding=_vector(0.9),
        metadata={"strategy": "semantic", "token_count": 99},
    )
    await repo.bulk_insert([updated])

    # Solo 1 chunk (no duplicado).
    assert await repo.count_for_document(doc_id) == 1


# ===========================================================================
# delete_by_document
# ===========================================================================


async def test_delete_by_document_removes_all_chunks(session_factory) -> None:  # type: ignore[no-untyped-def]
    suffix = uuid.uuid4().hex[:6]
    doc_id = f"POL-del-{suffix}-2026-05-23"
    await _create_test_document(session_factory, doc_id)
    repo = PostgresChunkRepository(session_factory)
    await repo.bulk_insert([_chunk(doc_id, i) for i in range(5)])

    deleted = await repo.delete_by_document(doc_id)
    assert deleted == 5

    assert await repo.count_for_document(doc_id) == 0


async def test_delete_by_document_idempotent_when_no_chunks(
    session_factory,  # type: ignore[no-untyped-def]
) -> None:
    """Borrar un doc sin chunks devuelve 0 sin lanzar error."""
    repo = PostgresChunkRepository(session_factory)
    deleted = await repo.delete_by_document("POL-empty-99-2026-01-01")
    assert deleted == 0


async def test_delete_by_document_only_affects_target_doc(
    session_factory,  # type: ignore[no-untyped-def]
) -> None:
    """Borrar chunks de doc A no debe tocar los de doc B."""
    suffix = uuid.uuid4().hex[:6]
    doc_a = f"POL-A-{suffix}-2026-05-23"
    doc_b = f"POL-B-{suffix}-2026-05-23"
    await _create_test_document(session_factory, doc_a)
    await _create_test_document(session_factory, doc_b)

    repo = PostgresChunkRepository(session_factory)
    await repo.bulk_insert([_chunk(doc_a, i) for i in range(3)])
    await repo.bulk_insert([_chunk(doc_b, i) for i in range(2)])

    await repo.delete_by_document(doc_a)

    assert await repo.count_for_document(doc_a) == 0
    assert await repo.count_for_document(doc_b) == 2


# ===========================================================================
# count_for_document
# ===========================================================================


async def test_count_for_document_zero_when_no_chunks(
    session_factory,  # type: ignore[no-untyped-def]
) -> None:
    repo = PostgresChunkRepository(session_factory)
    assert await repo.count_for_document("DOC-no-existe-99") == 0


async def test_count_for_document_reflects_inserts(
    session_factory,  # type: ignore[no-untyped-def]
) -> None:
    suffix = uuid.uuid4().hex[:6]
    doc_id = f"POL-count-{suffix}-2026-05-23"
    await _create_test_document(session_factory, doc_id)
    repo = PostgresChunkRepository(session_factory)

    await repo.bulk_insert([_chunk(doc_id, i) for i in range(7)])
    assert await repo.count_for_document(doc_id) == 7


# ===========================================================================
# pgvector roundtrip
# ===========================================================================


async def test_embedding_roundtrip_preserves_vector(
    session_factory,  # type: ignore[no-untyped-def]
) -> None:
    """Insert + select del embedding debe devolver el mismo vector."""
    from sqlalchemy import select

    suffix = uuid.uuid4().hex[:6]
    doc_id = f"POL-vec-{suffix}-2026-05-23"
    await _create_test_document(session_factory, doc_id)

    repo = PostgresChunkRepository(session_factory)
    expected = [0.1, 0.2, 0.3] + [0.0] * 1021
    await repo.bulk_insert([_chunk(doc_id, 0, vector=expected)])

    async with session_factory() as db:
        result = await db.execute(
            select(models.DocumentChunkModel.embedding).where(
                models.DocumentChunkModel.document_id == doc_id
            )
        )
        row = result.scalar_one()
        # pgvector devuelve un numpy array — convertimos a list para comparar.
        actual = list(row)
        assert len(actual) == 1024
        assert actual[0] == pytest.approx(0.1, rel=1e-6)
        assert actual[2] == pytest.approx(0.3, rel=1e-6)
