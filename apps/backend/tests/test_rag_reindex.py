"""Tests del módulo `rag/reindex` (Fase 3.6).

Usan fakes para `DocumentRepository` y `Indexer`. Sin Cohere ni DB.

Cubren:
- Iteración paginada (batch_size + offset).
- Filtros `carpetas` y `tipos` se propagan al `search()`.
- `text_source` se invoca por doc; vacío → skip + log warning.
- `--dry-run` no llama al indexer.
- Un error en un doc NO aborta la corrida — continúa con el siguiente.
- Stats finales (chunks_created, tokens, cost_usd, errores).
- `has_errors` property.
- Progress callback se invoca tras cada página.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import pytest

from sqa_kb.domain.entities import Document, DocumentDetail
from sqa_kb.domain.value_objects import CategoryCode, DocStatus, DocTypeCode
from sqa_kb.rag.chunker import Section
from sqa_kb.rag.indexer import IndexerResult
from sqa_kb.rag.reindex import (
    DEFAULT_BATCH_SIZE,
    ReindexStats,
    _default_text_source,
    reindex,
)

# ===========================================================================
# Fakes
# ===========================================================================


def _doc(
    slug: str,
    *,
    resumen: str = "Resumen del documento.",
    carpeta: str = "TEC",
    tipo: str = "POL",
) -> Document:
    """`Document.id` exige formato `<TIPO>-<slug>-<fecha>` (ROADMAP). El
    `slug` que recibe acá se sanitiza para entrar en el patrón.

    Nota: `Document` no tiene `resumen` — vive en `DocumentDetail`.
    El test stuffea `resumen` como atributo "lateral" para que el
    `_FakeDocRepo.get_detail` lo recupere fácil.
    """
    now = datetime.now(UTC)
    safe_slug = slug.lower().replace("_", "-")
    doc_id = f"{tipo}-{safe_slug}-2026-05-25"
    doc = Document(
        id=doc_id,
        titulo=f"Doc {slug}",
        carpeta=CategoryCode(carpeta),
        tipo=DocTypeCode(tipo),
        autoritativo=False,
        estado=DocStatus.VIGENTE,
        autor_name="A",
        autor_role="QA",
        fecha=now,
        revision=now,
        version="1.0",
        formato="MD",
    )
    # Para el fake, recordamos el resumen aparte (ver _FakeDocRepo.get_detail).
    _FAKE_RESUMENES[doc_id] = resumen
    return doc


# Mapa side-channel para que el fake `get_detail` recupere el resumen
# sin tener que materializar un `DocumentDetail` completo en cada test.
_FAKE_RESUMENES: dict[str, str] = {}


@dataclass
class _FakeDocRepo:
    """Imita el subset del puerto que `reindex` usa.

    `pages` es una lista de listas — cada llamada a `search()` consume
    una página (FIFO). Cuando se acaban, devuelve [] para que el while
    termine.
    """

    pages: list[list[Document]] = field(default_factory=list)
    search_calls: list[dict[str, Any]] = field(default_factory=list)

    async def search(  # noqa: PLR0913
        self,
        *,
        query: str | None = None,
        carpetas: object = None,
        tipos: object = None,
        estados: object = None,
        autoritativo: object = None,
        anonimizado: object = None,
        min_score: object = None,
        date_from: object = None,
        date_to: object = None,
        author_oid: object = None,
        sort_by: object = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[Sequence[Document], int]:
        self.search_calls.append(
            {
                "carpetas": list(carpetas) if carpetas else None,
                "tipos": list(tipos) if tipos else None,
                "limit": limit,
                "offset": offset,
            }
        )
        if not self.pages:
            return [], 0
        return self.pages.pop(0), 0

    async def get_detail(self, document_id: str) -> DocumentDetail | None:
        """Devuelve un `DocumentDetail` armado al vuelo con el `resumen`
        que el helper `_doc()` registró en `_FAKE_RESUMENES`."""
        resumen = _FAKE_RESUMENES.get(document_id)
        if resumen is None:
            return None
        now = datetime.now(UTC)
        return DocumentDetail(
            id=document_id,
            titulo=f"Doc {document_id}",
            carpeta=CategoryCode.TEC,
            tipo=DocTypeCode.POL,
            autoritativo=False,
            estado=DocStatus.VIGENTE,
            autor_name="A",
            autor_role="QA",
            fecha=now,
            revision=now,
            version="1.0",
            formato="MD",
            resumen=resumen,
        )


@dataclass
class _FakeIndexer:
    """Imita el `Indexer` real. Cada `index_document` registra el llamado
    y devuelve un `IndexerResult` con números configurables."""

    chunks_per_doc: int = 3
    tokens_per_doc: int = 50
    cost_per_doc: float = 0.001
    fail_on_ids: tuple[str, ...] = ()
    calls: list[dict[str, Any]] = field(default_factory=list)

    async def index_document(
        self, document_id: str, *, sections, text=None, replace=True  # type: ignore[no-untyped-def]
    ) -> IndexerResult:
        self.calls.append(
            {
                "document_id": document_id,
                "sections": list(sections),
                "text": text,
                "replace": replace,
            }
        )
        if document_id in self.fail_on_ids:
            raise RuntimeError(f"falla simulada en {document_id}")
        return IndexerResult(
            document_id=document_id,
            chunks_created=self.chunks_per_doc,
            tokens_embedded=self.tokens_per_doc,
            cost_usd=self.cost_per_doc,
            sub_batches=1,
            replaced_old_chunks=0,
        )


# ===========================================================================
# _default_text_source
# ===========================================================================


async def test_default_text_source_uses_resumen_as_section() -> None:
    repo = _FakeDocRepo()
    doc = _doc("D1", resumen="resumen ejecutivo del documento")
    sections, text = await _default_text_source(repo, doc)  # type: ignore[arg-type]
    assert text is None
    assert len(sections) == 1
    assert sections[0].title == doc.titulo
    assert sections[0].content == "resumen ejecutivo del documento"


async def test_default_text_source_empty_resumen_returns_empty() -> None:
    repo = _FakeDocRepo()
    doc = _doc("D-empty", resumen="")
    sections, text = await _default_text_source(repo, doc)  # type: ignore[arg-type]
    assert sections == [] and text is None


async def test_default_text_source_whitespace_only_resumen_returns_empty() -> None:
    repo = _FakeDocRepo()
    doc = _doc("D-ws", resumen="   \n\t  ")
    sections, text = await _default_text_source(repo, doc)  # type: ignore[arg-type]
    assert sections == [] and text is None


async def test_default_text_source_returns_empty_when_no_detail() -> None:
    """Si `repo.get_detail` devuelve None (doc no existe), skip silencioso."""
    repo = _FakeDocRepo()
    # Creamos un Document SIN registrar el resumen en _FAKE_RESUMENES.
    now = datetime.now(UTC)
    doc = Document(
        id="POL-orphan-2026-05-25",
        titulo="Orphan",
        carpeta=CategoryCode.TEC,
        tipo=DocTypeCode.POL,
        autoritativo=False,
        estado=DocStatus.VIGENTE,
        autor_name="A",
        autor_role="QA",
        fecha=now,
        revision=now,
        version="1.0",
        formato="MD",
    )
    sections, text = await _default_text_source(repo, doc)  # type: ignore[arg-type]
    assert sections == [] and text is None


# ===========================================================================
# reindex — happy path + paginación
# ===========================================================================


async def test_reindex_processes_all_docs_in_single_page() -> None:
    docs = [_doc(f"D{i}") for i in range(3)]
    repo = _FakeDocRepo(pages=[docs])
    indexer = _FakeIndexer()

    stats = await reindex(
        document_repo=repo,  # type: ignore[arg-type]
        indexer=indexer,  # type: ignore[arg-type]
        batch_size=50,
    )

    assert stats.docs_processed == 3
    assert stats.docs_indexed == 3
    assert stats.docs_skipped == 0
    assert stats.docs_failed == 0
    assert stats.chunks_created == 9  # 3 × 3
    assert stats.tokens_embedded == 150
    assert stats.cost_usd == pytest.approx(0.003)
    assert len(indexer.calls) == 3


async def test_reindex_paginates_until_repo_empty() -> None:
    """3 páginas: 50 + 50 + 10 docs → batch_size=50. La última corta el loop."""
    page1 = [_doc(f"A{i}") for i in range(50)]
    page2 = [_doc(f"B{i}") for i in range(50)]
    page3 = [_doc(f"C{i}") for i in range(10)]
    repo = _FakeDocRepo(pages=[page1, page2, page3])
    indexer = _FakeIndexer()

    stats = await reindex(
        document_repo=repo,  # type: ignore[arg-type]
        indexer=indexer,  # type: ignore[arg-type]
        batch_size=50,
    )
    assert stats.docs_processed == 110
    assert stats.docs_indexed == 110
    # Offset progresa correctamente.
    offsets = [c["offset"] for c in repo.search_calls]
    assert offsets == [0, 50, 100]


async def test_reindex_stops_when_repo_returns_short_page() -> None:
    """Si la primera página viene incompleta (< batch_size), no pide otra."""
    docs = [_doc(f"D{i}") for i in range(5)]
    repo = _FakeDocRepo(pages=[docs])
    indexer = _FakeIndexer()

    await reindex(
        document_repo=repo,  # type: ignore[arg-type]
        indexer=indexer,  # type: ignore[arg-type]
        batch_size=50,
    )
    assert len(repo.search_calls) == 1


# ===========================================================================
# Filtros
# ===========================================================================


async def test_reindex_passes_carpetas_filter_to_search() -> None:
    repo = _FakeDocRepo(pages=[[_doc("D1")]])
    indexer = _FakeIndexer()
    await reindex(
        document_repo=repo,  # type: ignore[arg-type]
        indexer=indexer,  # type: ignore[arg-type]
        carpetas=[CategoryCode.TEC, CategoryCode.ARQ],
    )
    assert repo.search_calls[0]["carpetas"] == [CategoryCode.TEC, CategoryCode.ARQ]


async def test_reindex_passes_tipos_filter_to_search() -> None:
    repo = _FakeDocRepo(pages=[[_doc("D1")]])
    indexer = _FakeIndexer()
    await reindex(
        document_repo=repo,  # type: ignore[arg-type]
        indexer=indexer,  # type: ignore[arg-type]
        tipos=[DocTypeCode.POL],
    )
    assert repo.search_calls[0]["tipos"] == [DocTypeCode.POL]


# ===========================================================================
# Skip docs sin texto
# ===========================================================================


async def test_reindex_skips_docs_with_empty_resumen(caplog: Any) -> None:
    """Default text_source devuelve vacío para resumen vacío → skip."""
    doc_empty = _doc("Dempty", resumen="")
    doc_full = _doc("Dfull", resumen="contenido real")
    docs = [doc_empty, doc_full]
    repo = _FakeDocRepo(pages=[docs])
    indexer = _FakeIndexer()

    with caplog.at_level(logging.WARNING):
        stats = await reindex(
            document_repo=repo,  # type: ignore[arg-type]
            indexer=indexer,  # type: ignore[arg-type]
        )

    assert stats.docs_processed == 2
    assert stats.docs_indexed == 1
    assert stats.docs_skipped == 1
    assert stats.docs_failed == 0
    assert len(indexer.calls) == 1
    assert indexer.calls[0]["document_id"] == doc_full.id
    # Warning loggeado.
    assert any(f"Skipping {doc_empty.id}" in rec.message for rec in caplog.records)


# ===========================================================================
# --dry-run
# ===========================================================================


async def test_reindex_dry_run_does_not_call_indexer() -> None:
    docs = [_doc(f"D{i}") for i in range(3)]
    repo = _FakeDocRepo(pages=[docs])
    indexer = _FakeIndexer()

    stats = await reindex(
        document_repo=repo,  # type: ignore[arg-type]
        indexer=indexer,  # type: ignore[arg-type]
        dry_run=True,
    )
    assert stats.docs_processed == 3
    assert stats.docs_indexed == 3  # contados para planning
    assert stats.chunks_created == 0  # pero sin tocar el indexer
    assert stats.tokens_embedded == 0
    assert stats.cost_usd == 0.0
    assert indexer.calls == []


# ===========================================================================
# Resiliencia ante errores
# ===========================================================================


async def test_reindex_one_failed_doc_does_not_abort_batch(caplog: Any) -> None:
    """Un doc que falla NO aborta la corrida — los demás siguen indexándose."""
    doc_ok1 = _doc("D1")
    doc_bad = _doc("Dbad")
    doc_ok3 = _doc("D3")
    docs = [doc_ok1, doc_bad, doc_ok3]
    repo = _FakeDocRepo(pages=[docs])
    indexer = _FakeIndexer(fail_on_ids=(doc_bad.id,))

    with caplog.at_level(logging.ERROR):
        stats = await reindex(
            document_repo=repo,  # type: ignore[arg-type]
            indexer=indexer,  # type: ignore[arg-type]
        )

    assert stats.docs_processed == 3
    assert stats.docs_indexed == 2
    assert stats.docs_failed == 1
    assert stats.has_errors is True
    assert len(indexer.calls) == 3  # los 3 fueron intentados


async def test_reindex_text_source_exception_counts_as_failure(caplog: Any) -> None:
    """Si `text_source` rota, se cuenta como failure y se continúa."""

    async def _broken_source(
        repo,  # type: ignore[no-untyped-def] # noqa: ARG001
        doc: Document,
    ) -> tuple[Sequence[Section], str | None]:
        if "bad" in doc.id:
            raise RuntimeError("text source roto")
        return ([Section(title=doc.titulo, content="ok")], None)

    docs = [_doc("D1"), _doc("Dbad"), _doc("D3")]
    repo = _FakeDocRepo(pages=[docs])
    indexer = _FakeIndexer()

    with caplog.at_level(logging.ERROR):
        stats = await reindex(
            document_repo=repo,  # type: ignore[arg-type]
            indexer=indexer,  # type: ignore[arg-type]
            text_source=_broken_source,
        )

    assert stats.docs_failed == 1
    assert stats.docs_indexed == 2
    # El indexer SOLO se llamó para los 2 docs OK (Dbad falló antes).
    bad_id = next(d.id for d in docs if "bad" in d.id)
    indexed_ids = {c["document_id"] for c in indexer.calls}
    assert bad_id not in indexed_ids
    assert len(indexed_ids) == 2


async def test_reindex_stats_have_errors_false_when_clean() -> None:
    repo = _FakeDocRepo(pages=[[_doc("D1")]])
    indexer = _FakeIndexer()
    stats = await reindex(
        document_repo=repo,  # type: ignore[arg-type]
        indexer=indexer,  # type: ignore[arg-type]
    )
    assert stats.has_errors is False


# ===========================================================================
# Custom text_source (Fase 4 lo usará para Blob)
# ===========================================================================


async def test_reindex_uses_custom_text_source() -> None:
    """Un caller puede pasar su propia función de text_source.

    Fase 4 usará esto para inyectar un text_source que baje el blob real.
    """

    async def _custom_source(
        repo,  # type: ignore[no-untyped-def] # noqa: ARG001
        doc: Document,
    ) -> tuple[Sequence[Section], str | None]:
        return ([Section(title="Custom", content=f"custom-{doc.id}")], None)

    docs = [_doc("D1"), _doc("D2")]
    repo = _FakeDocRepo(pages=[docs])
    indexer = _FakeIndexer()

    await reindex(
        document_repo=repo,  # type: ignore[arg-type]
        indexer=indexer,  # type: ignore[arg-type]
        text_source=_custom_source,
    )
    assert indexer.calls[0]["sections"][0].content.startswith("custom-POL-d1")
    assert indexer.calls[1]["sections"][0].content.startswith("custom-POL-d2")


# ===========================================================================
# Progress callback
# ===========================================================================


async def test_reindex_progress_callback_invoked_per_page() -> None:
    """El callback se llama tras procesar cada página completa."""
    page1 = [_doc(f"A{i}") for i in range(50)]
    page2 = [_doc(f"B{i}") for i in range(10)]
    repo = _FakeDocRepo(pages=[page1, page2])
    indexer = _FakeIndexer()
    progresses: list[ReindexStats] = []

    async def _cb(s: ReindexStats) -> None:
        progresses.append(s)

    await reindex(
        document_repo=repo,  # type: ignore[arg-type]
        indexer=indexer,  # type: ignore[arg-type]
        batch_size=50,
        progress_callback=_cb,
    )

    assert len(progresses) == 2
    assert progresses[0].docs_processed == 50
    assert progresses[1].docs_processed == 60


# ===========================================================================
# Edge: repo vacío
# ===========================================================================


async def test_reindex_empty_repo_returns_zero_stats() -> None:
    repo = _FakeDocRepo(pages=[])
    indexer = _FakeIndexer()
    stats = await reindex(
        document_repo=repo,  # type: ignore[arg-type]
        indexer=indexer,  # type: ignore[arg-type]
    )
    assert stats.docs_processed == 0
    assert stats.has_errors is False
    assert indexer.calls == []


# ===========================================================================
# Default batch size constant
# ===========================================================================


def test_default_batch_size_constant() -> None:
    assert DEFAULT_BATCH_SIZE == 50
