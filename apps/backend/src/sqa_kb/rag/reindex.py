"""Reindex batch — lógica reusable del script CLI (Fase 3.6).

La función `reindex()` toma todas sus dependencias inyectadas (repo,
indexer, text_source) y procesa documentos en lotes paginados. El
CLI (`scripts/reindex_all.py`) la invoca con los adapters reales; los
tests la invocan con fakes y verifican el comportamiento.

**Diseño de `text_source`**
==========================
En Fase 3 no hay Blob cableado — el `content` completo de un documento
no está persistido en la tabla `documents` (el campo `resumen` vive en
el agregado `DocumentDetail`, no en `Document`). El reindex acepta una
función `text_source(repo, doc) -> Awaitable[tuple[Sequence[Section],
str | None]]` para desacoplar el "de dónde sale el texto" del "cómo se
indexa". Es **async** porque puede tener que pegarle al repo (o Blob,
en Fase 4) para resolver el texto.

- `_default_text_source` (Fase 3): hace `repo.get_detail(doc.id)` y
  usa el `resumen` como única `Section`. Si está vacío, devuelve
  `([], None)` y `reindex()` skipea con warning.
- Fase 4 cableará un `text_source` que descargue el blob y devuelva
  secciones reales del extractor.

**Resiliencia**
==============
Un error en un documento NO aborta la corrida — se loggea y se
continúa con el siguiente. Los stats finales reportan cuántos errores
hubo. Esto permite, p.ej., correr el reindex sobre 1000 docs cuando
20 tienen contenido corrupto sin bloquear el resto.
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable, Iterable, Sequence
from dataclasses import dataclass

from sqa_kb.domain.entities import Document
from sqa_kb.domain.value_objects import CategoryCode, DocTypeCode
from sqa_kb.ports.repositories import DocumentRepository
from sqa_kb.rag.chunker import Section
from sqa_kb.rag.indexer import Indexer

logger = logging.getLogger(__name__)


DEFAULT_BATCH_SIZE: int = 50
"""Cuántos documentos paginar por iteración. Balance entre memoria
(traer 5000 docs de una es mucho) y latencia (paginar 1 por vez es
lento). 50 es razonable para la mayoría de los catálogos."""


TextSource = Callable[
    [DocumentRepository, Document],
    Awaitable[tuple[Sequence[Section], str | None]],
]
"""Función inyectable que devuelve `(sections, text)` para un doc.

Es **async** porque puede tener que pegarle al repo (o Blob, en Fase 4)
para resolver el contenido del documento.

- `sections=[]` y `text=None` → reindex skipea el doc sin fallar.
- `sections=[...]` → el chunker procesa esas secciones.
- `text="..."` (sin secciones) → el chunker arma una sola Section con
  todo el texto.
"""


async def _default_text_source(
    repo: DocumentRepository, doc: Document
) -> tuple[Sequence[Section], str | None]:
    """Default Fase 3: hace `repo.get_detail(doc.id)` y usa el `resumen`.

    Fase 4 reemplaza esta función con una que baje el blob + invoque
    el extractor.
    """
    detail = await repo.get_detail(doc.id)
    if detail is None or not detail.resumen or not detail.resumen.strip():
        return ([], None)
    return ([Section(title=doc.titulo, content=detail.resumen)], None)


@dataclass(frozen=True, slots=True)
class ReindexStats:
    """Métricas finales de una corrida del reindex."""

    docs_processed: int
    """Cuántos docs el repo devolvió y el script intentó procesar."""
    docs_indexed: int
    """Cuántos docs se indexaron exitosamente (con chunks creados)."""
    docs_skipped: int
    """Cuántos docs se skipearon por no tener texto (text_source vacío)."""
    docs_failed: int
    """Cuántos docs fallaron durante chunk/embed/insert."""
    chunks_created: int
    tokens_embedded: int
    cost_usd: float

    @property
    def has_errors(self) -> bool:
        return self.docs_failed > 0


@dataclass
class _MutableStats:
    """Helper interno — `ReindexStats` es frozen, este se muta durante
    la corrida y al final se convierte al inmutable."""

    docs_processed: int = 0
    docs_indexed: int = 0
    docs_skipped: int = 0
    docs_failed: int = 0
    chunks_created: int = 0
    tokens_embedded: int = 0
    cost_usd: float = 0.0

    def freeze(self) -> ReindexStats:
        return ReindexStats(
            docs_processed=self.docs_processed,
            docs_indexed=self.docs_indexed,
            docs_skipped=self.docs_skipped,
            docs_failed=self.docs_failed,
            chunks_created=self.chunks_created,
            tokens_embedded=self.tokens_embedded,
            cost_usd=round(self.cost_usd, 6),
        )


async def reindex(
    *,
    document_repo: DocumentRepository,
    indexer: Indexer,
    text_source: TextSource = _default_text_source,
    carpetas: Iterable[CategoryCode] | None = None,
    tipos: Iterable[DocTypeCode] | None = None,
    batch_size: int = DEFAULT_BATCH_SIZE,
    dry_run: bool = False,
    progress_callback: Callable[[ReindexStats], Awaitable[None]] | None = None,
) -> ReindexStats:
    """Itera todos los docs que matchean los filtros y los indexa.

    Args:
        document_repo: para iterar el catálogo (`search()` paginado).
        indexer: para llamar `index_document()`. `dry_run=True` lo evita.
        text_source: callable que devuelve `(sections, text)` por doc.
        carpetas: filtro opcional por carpeta.
        tipos: filtro opcional por tipo de documento.
        batch_size: cuántos docs traer por página.
        dry_run: si True, NO llama al indexer (solo cuenta cuántos
            procesaría). Útil para validar filtros antes de un run grande.
        progress_callback: callback opcional invocado tras procesar cada
            página — permite reportar avance en CLIs largos.

    Devuelve `ReindexStats` con los conteos finales.
    """
    stats = _MutableStats()
    offset = 0

    while True:
        items, _total = await document_repo.search(
            carpetas=carpetas,
            tipos=tipos,
            limit=batch_size,
            offset=offset,
        )
        if not items:
            break

        for doc in items:
            stats.docs_processed += 1
            try:
                sections, text = await text_source(document_repo, doc)
            except Exception as exc:  # noqa: BLE001
                logger.exception(
                    "text_source falló para %s: %s", doc.id, exc
                )
                stats.docs_failed += 1
                continue

            if not sections and not text:
                logger.warning(
                    "Skipping %s — text_source devolvió vacío", doc.id
                )
                stats.docs_skipped += 1
                continue

            if dry_run:
                # En dry-run contamos como indexado para fines de
                # planning, pero sin tocar el indexer.
                stats.docs_indexed += 1
                continue

            try:
                result = await indexer.index_document(
                    doc.id, sections=sections, text=text
                )
            except Exception as exc:  # noqa: BLE001 — un doc no aborta el batch
                logger.exception(
                    "Indexer falló para %s: %s", doc.id, exc
                )
                stats.docs_failed += 1
                continue

            stats.docs_indexed += 1
            stats.chunks_created += result.chunks_created
            stats.tokens_embedded += result.tokens_embedded
            stats.cost_usd += result.cost_usd

        if progress_callback is not None:
            await progress_callback(stats.freeze())

        # Si la página vino con menos items que `batch_size`, no hay más.
        if len(items) < batch_size:
            break
        offset += batch_size

    return stats.freeze()
