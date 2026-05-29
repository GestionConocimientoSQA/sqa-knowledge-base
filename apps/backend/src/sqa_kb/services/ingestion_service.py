"""IngestionService — orquesta el flujo del modo C (Fase 4.5).

Coordina los puertos/componentes de la ingesta de documentación
aprobada:

    upload   → Blob + crear IngestionItem (status=pendiente-metadata)
    classify → descarga Blob → extrae texto → anonimiza → clasifica (LLM)
               → actualiza item (carpeta/tipo sugeridos, status=en-revision)
    approve  → crea Document + dispara indexación → item status=indexado
    list     → lista items filtrable por status

Diseño SOLID: el servicio recibe TODAS sus dependencias por constructor
(puertos), no las construye. El router HTTP (`api/ingestion.py`) es un
thin wrapper que valida el request y delega acá. Esto permite testear
el flujo completo con fakes, sin HTTP ni Azure.

Componentes inyectados:
- `ingestion_repo` (IngestionRepository): persistencia del item.
- `document_repo` (DocumentRepository): crear el Document al aprobar.
- `blob` (BlobStorage): subir/descargar el archivo.
- `extractor` (ExtractorDispatcher): texto+estructura desde el archivo.
- `anonymizer` (PiiFilter): limpiar PII antes de clasificar/indexar.
- `classifier` (Callable async): clasifica el texto → (carpeta, tipo).
  Se inyecta como callable para no acoplar el servicio al LlmGateway ni
  al agente — el wiring le pasa una lambda que llama `classify_topic`.
- `indexer_hook` (Callable async | None): dispara la indexación del doc
  aprobado. None = no indexar (entornos sin Cohere).
"""

from __future__ import annotations

import logging
import uuid
from collections.abc import Awaitable, Callable, Iterable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime

from sqa_kb.documents.extractors import ExtractorDispatcher, UnsupportedFormatError
from sqa_kb.documents.filename import build_filename
from sqa_kb.domain.entities import Document, IngestionItem
from sqa_kb.domain.errors import NotFoundError, ValidationError
from sqa_kb.domain.value_objects import (
    CategoryCode,
    DocStatus,
    DocTypeCode,
    IngestionStatus,
)
from sqa_kb.ports.gateways import BlobStorage, PiiFilter
from sqa_kb.ports.repositories import DocumentRepository, IngestionRepository

# Contenedor de Blob donde viven los uploads pendientes de ingesta.
INBOX_CONTAINER = "inbox-pendientes"

# Tope de tamaño de upload (10 MB) — espejo del límite del frontend.
MAX_UPLOAD_BYTES = 10 * 1024 * 1024


@dataclass(frozen=True, slots=True)
class ClassificationSuggestion:
    """Resultado de la clasificación automática de un item."""

    category: CategoryCode
    document_type: DocTypeCode
    confidence: float
    reasoning: str


# El clasificador se inyecta como callable: recibe el texto extraído y
# devuelve una sugerencia. El wiring lo cablea a `classify_topic` del
# agente; los tests pasan un fake determinista.
ClassifierFn = Callable[[str], Awaitable[ClassificationSuggestion]]

# Hook de indexación: recibe (document_id, texto) y persiste chunks.
IndexerHook = Callable[[str, str], Awaitable[None]]


@dataclass(frozen=True, slots=True)
class TraceabilityInput:
    """Metadata de trazabilidad obligatoria al aprobar (§16 ROADMAP)."""

    approved_by: str
    approval_date: str
    source_origin: str
    version: str
    category: CategoryCode
    document_type: DocTypeCode


class IngestionService:
    """Orquesta el flujo de ingesta (modo C)."""

    def __init__(
        self,
        *,
        ingestion_repo: IngestionRepository,
        document_repo: DocumentRepository,
        blob: BlobStorage,
        anonymizer: PiiFilter,
        classifier: ClassifierFn,
        extractor: ExtractorDispatcher | None = None,
        indexer_hook: IndexerHook | None = None,
    ) -> None:
        self._ingestion_repo = ingestion_repo
        self._document_repo = document_repo
        self._blob = blob
        self._anonymizer = anonymizer
        self._classifier = classifier
        self._extractor = extractor or ExtractorDispatcher()
        self._indexer_hook = indexer_hook

    # -- upload -------------------------------------------------------------

    async def upload(
        self,
        *,
        filename: str,
        data: bytes,
        uploaded_by_oid: str,
        project_id: str,
        source_origin: str = "",
    ) -> IngestionItem:
        """Valida + sube el archivo al Blob + crea el IngestionItem.

        `project_id` es obligatorio desde Fase 9.3 — el item queda asociado
        al proyecto para que el `project_owner` lo apruebe y el doc final
        herede el scoping. El caller (endpoint) valida la membership antes
        de invocar.

        Lanza `ValidationError` si el archivo es muy grande o el formato
        no tiene extractor.
        """
        if len(data) == 0:
            raise ValidationError("El archivo está vacío.")
        if len(data) > MAX_UPLOAD_BYTES:
            raise ValidationError(
                f"El archivo supera el límite de {MAX_UPLOAD_BYTES // (1024 * 1024)} MB."
            )
        if not self._extractor.supports(filename):
            raise ValidationError(
                f"Formato no soportado. Soportados: "
                f"{', '.join(self._extractor.supported_extensions)}."
            )

        item_id = f"ing-{uuid.uuid4().hex[:12]}"
        blob_path = f"{item_id}/{filename}"
        await self._blob.upload(
            container=INBOX_CONTAINER,
            path=blob_path,
            data=data,
            content_type="application/octet-stream",
        )
        item = IngestionItem(
            id=item_id,
            project_id=project_id,
            filename=filename,
            size_bytes=len(data),
            status=IngestionStatus.PENDIENTE_METADATA,
            uploaded_by_oid=uploaded_by_oid,
            uploaded_at=datetime.now(UTC),
            blob_path=blob_path,
            fuente_original=source_origin,
        )
        return await self._ingestion_repo.create(item)

    # -- classify -----------------------------------------------------------

    async def classify(self, item_id: str) -> IngestionItem:
        """Descarga el archivo, extrae texto, anonimiza y clasifica.

        Actualiza el item con carpeta/tipo sugeridos + páginas detectadas
        y lo pasa a `en-revision`. Si la extracción falla, marca el item
        `rechazado` con el motivo.
        """
        item = await self._ingestion_repo.get(item_id)
        if item is None:
            raise NotFoundError(f"Item de ingesta {item_id} no encontrado")
        if item.blob_path is None:
            raise ValidationError(f"El item {item_id} no tiene archivo asociado.")

        data = await self._blob.download(
            container=INBOX_CONTAINER, path=item.blob_path
        )
        try:
            extracted = self._extractor.extract(item.filename, data)
        except UnsupportedFormatError as exc:
            return await self._reject(item, f"Formato no soportado: {exc}")

        if extracted.is_empty:
            return await self._reject(item, "No se pudo extraer texto del archivo.")

        # Anonimizar antes de mandar al clasificador (no filtrar PII al LLM).
        anon = await self._anonymizer.anonymize(extracted.text)
        suggestion = await self._classifier(anon.text)

        updated = item.model_copy(
            update={
                "carpeta_sugerida": suggestion.category,
                "tipo_sugerido": suggestion.document_type,
                "paginas": max(extracted.page_count, 1),
                "status": IngestionStatus.EN_REVISION,
                "error_detail": None,
            }
        )
        return await self._ingestion_repo.update(updated)

    # -- approve ------------------------------------------------------------

    async def approve(
        self,
        item_id: str,
        *,
        traceability: TraceabilityInput,
        approver_oid: str,
        approver_name: str,
    ) -> IngestionItem:
        """Crea el Document final con la trazabilidad, dispara la
        indexación y marca el item `indexado`."""
        item = await self._ingestion_repo.get(item_id)
        if item is None:
            raise NotFoundError(f"Item de ingesta {item_id} no encontrado")
        if item.blob_path is None:
            raise ValidationError(f"El item {item_id} no tiene archivo asociado.")

        # Re-extraer + anonimizar para indexar el contenido limpio.
        data = await self._blob.download(
            container=INBOX_CONTAINER, path=item.blob_path
        )
        extracted = self._extractor.extract(item.filename, data)
        anon = await self._anonymizer.anonymize(extracted.text)

        now = datetime.now(UTC)
        title = _title_from_filename(item.filename)
        document_id = build_filename(
            document_type=str(traceability.document_type),
            topic=title,
            fecha=now,
            extension="",
        )
        document = Document(
            id=document_id,
            project_id=item.project_id,
            titulo=title,
            carpeta=traceability.category,
            tipo=traceability.document_type,
            autoritativo=False,
            estado=DocStatus.VIGENTE,
            autor_oid=approver_oid,
            autor_name=approver_name,
            autor_role="ingesta",
            fecha=now,
            revision=now,
            version=traceability.version or "1.0",
            formato=_format_from_filename(item.filename),
            anonimizado=anon.replacements > 0,
            aprobador_name=traceability.approved_by,
            fecha_aprobacion=_parse_date_safe(traceability.approval_date),
        )
        await self._document_repo.create(document)

        if self._indexer_hook is not None:
            await self._indexer_hook(document.id, anon.text)

        updated = item.model_copy(
            update={
                "status": IngestionStatus.INDEXADO,
                "aprobador_oid": approver_oid,
                "aprobador_name": traceability.approved_by,
                "fecha_aprobacion": _parse_date_safe(traceability.approval_date),
                "fuente_original": traceability.source_origin or item.fuente_original,
                "version": traceability.version,
                "carpeta_sugerida": traceability.category,
                "tipo_sugerido": traceability.document_type,
            }
        )
        return await self._ingestion_repo.update(updated)

    # -- reject -------------------------------------------------------------

    async def reject(self, item_id: str, *, reason: str) -> IngestionItem:
        """Rechaza un item (decisión del revisor). Marca `rechazado` con
        el motivo en `error_detail`. El archivo en Blob queda — se puede
        re-subir o auditar."""
        item = await self._ingestion_repo.get(item_id)
        if item is None:
            raise NotFoundError(f"Item de ingesta {item_id} no encontrado")
        return await self._reject(item, reason or "Rechazado por el revisor.")

    # -- list ---------------------------------------------------------------

    async def list_items(
        self,
        *,
        statuses: Iterable[IngestionStatus] | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Sequence[IngestionItem]:
        return await self._ingestion_repo.list_by_status(
            statuses, limit=limit, offset=offset
        )

    # -- helpers ------------------------------------------------------------

    async def _reject(self, item: IngestionItem, reason: str) -> IngestionItem:
        updated = item.model_copy(
            update={
                "status": IngestionStatus.RECHAZADO,
                "error_detail": reason,
            }
        )
        return await self._ingestion_repo.update(updated)


def _title_from_filename(filename: str) -> str:
    """Deriva un título legible del nombre del archivo (sin extensión)."""
    from pathlib import PurePosixPath

    stem = PurePosixPath(filename).stem
    cleaned = stem.replace("_", " ").replace("-", " ").strip()
    return cleaned[:1].upper() + cleaned[1:] if cleaned else "Documento sin título"


def _format_from_filename(filename: str) -> str:
    from pathlib import PurePosixPath

    ext = PurePosixPath(filename).suffix.lstrip(".").upper()
    return ext or "MD"


def _parse_date_safe(value: str | None) -> datetime | None:
    """Parsea una fecha ISO (YYYY-MM-DD) tolerante. None si no parsea."""
    if not value:
        return None
    try:
        return datetime.fromisoformat(value).replace(tzinfo=UTC)
    except ValueError:
        return None


logger = logging.getLogger(__name__)


async def process_ingestion_background(
    service: IngestionService, item_id: str
) -> None:
    """Worker `ingestion_processor` (Fase 4.6) — auto-clasifica un item
    recién subido en background.

    Pensado para `FastAPI.BackgroundTasks`: tras el upload, el item se
    clasifica solo para que cuando el usuario lo abra en la UI ya tenga
    carpeta/tipo sugeridos. Swallowea excepciones + loggea (igual que
    `index_document_background`): si la auto-clasificación falla, el item
    queda en `pendiente-metadata` o `rechazado` y se puede reintentar
    con un POST /classify manual.
    """
    try:
        item = await service.classify(item_id)
        logger.info(
            "ingestion_autoclassified",
            extra={"item_id": item_id, "status": str(item.status)},
        )
    except Exception as exc:  # noqa: BLE001 — background task, fail safe
        logger.exception(
            "ingestion_autoclassify_failed",
            extra={"item_id": item_id, "error": str(exc)},
        )
