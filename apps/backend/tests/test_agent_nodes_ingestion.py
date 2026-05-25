"""Tests de los nodos de modo C (Fase 2.5).

Cubren:
- ingestion_classify: sin contenido → pide, con contenido → clasifica +
  Command(goto=ingestion_traceability), classify falla → reintento.
- ingestion_traceability: prompt inicial, parser de fecha/url/version,
  defaults cuando faltan campos, Command(goto=index_ingestion).
- index_ingestion: happy path crea Document + IngestionItem, faltan
  campos → error, repo falla → last_error.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from langgraph.types import Command

from sqa_kb.agent.nodes import (
    make_index_ingestion_node,
    make_ingestion_classify_node,
    make_ingestion_traceability_node,
)
from sqa_kb.agent.nodes.ingestion_traceability import _parse_traceability
from sqa_kb.agent.state import (
    AgentState,
    Classification,
    Traceability,
    initial_state,
)
from sqa_kb.domain.entities import Document, IngestionItem
from sqa_kb.ports.gateways import ChatMessage, LlmCompletion

# ===========================================================================
# Fakes
# ===========================================================================


@dataclass
class _FakeDocRepo:
    created: list[Document] = field(default_factory=list)
    should_fail: bool = False

    async def create(self, document: Document) -> Document:
        if self.should_fail:
            raise RuntimeError("doc repo fail")
        self.created.append(document)
        return document


@dataclass
class _FakeIngestRepo:
    created: list[IngestionItem] = field(default_factory=list)
    should_fail: bool = False

    async def create(self, item: IngestionItem) -> IngestionItem:
        if self.should_fail:
            raise RuntimeError("ingest repo fail")
        self.created.append(item)
        return item


@dataclass
class _FakeGateway:
    response_text: str = (
        '{"category":"TEC","document_type":"MTEC",'
        '"confidence":0.85,"reasoning":"técnico"}'
    )
    should_fail: bool = False

    async def complete(
        self,
        messages: Sequence[ChatMessage],
        *,
        model: str | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.7,
        metadata: Mapping[str, str] | None = None,
    ) -> LlmCompletion:
        if self.should_fail:
            raise RuntimeError("LLM down")
        return LlmCompletion(
            text=self.response_text,
            input_tokens=10,
            output_tokens=5,
            cost_usd=0.0001,
            model=model or "claude-sonnet-4-5",
        )

    async def stream(self, *args, **kwargs):  # type: ignore[no-untyped-def]
        raise NotImplementedError


def _state(mode: str = "ingestion") -> AgentState:
    return initial_state(
        session_id="ses-1", user_id="oid-1", user_name="Andrés", mode=mode  # type: ignore[arg-type]
    )


def _add_user(state: AgentState, content: str) -> None:
    state.messages.append({"role": "user", "content": content, "stage": None})


def _unwrap(result: dict[str, Any] | Command) -> dict[str, Any]:
    if isinstance(result, Command):
        return result.update or {}
    return result


def _goto(result: dict[str, Any] | Command) -> str | None:
    return result.goto if isinstance(result, Command) else None


# ===========================================================================
# ingestion_classify
# ===========================================================================


async def test_ingestion_classify_asks_for_content_when_empty() -> None:
    state = _state()
    node = make_ingestion_classify_node(gateway=_FakeGateway())  # type: ignore[arg-type]
    update = await node(state)
    assert "Pegame el contenido" in _unwrap(update)["messages"][0]["content"]


async def test_ingestion_classify_classifies_and_chains() -> None:
    state = _state()
    _add_user(state, "# Política de retención\n\nLos datos se guardan por 90 días.")
    node = make_ingestion_classify_node(gateway=_FakeGateway())  # type: ignore[arg-type]
    result = await node(state)
    assert _goto(result) == "ingestion_traceability"
    upd = _unwrap(result)
    assert upd["extracted_text"].startswith("# Política")
    assert upd["suggested_classification"] is not None
    assert upd["suggested_classification"].category == "TEC"


async def test_ingestion_classify_includes_preview_in_message() -> None:
    state = _state()
    long_text = "Este es el contenido del documento. " * 30  # >280 chars
    _add_user(state, long_text)
    node = make_ingestion_classify_node(gateway=_FakeGateway())  # type: ignore[arg-type]
    result = await node(state)
    msg = _unwrap(result)["messages"][0]
    assert "..." in msg["content"]  # preview truncado
    assert "Este es el contenido" in msg["content"]


async def test_ingestion_classify_handles_llm_error() -> None:
    state = _state()
    _add_user(state, "contenido")
    node = make_ingestion_classify_node(gateway=_FakeGateway(should_fail=True))  # type: ignore[arg-type]
    update = await node(state)
    upd = _unwrap(update)
    assert "No pude clasificar" in upd["messages"][0]["content"]
    assert upd["last_error"] == "classify_failed"


async def test_ingestion_classify_approximates_sections_from_markdown() -> None:
    state = _state()
    _add_user(
        state, "# Sección 1\nfoo\n# Sección 2\nbar\n# Sección 3\nbaz"
    )
    node = make_ingestion_classify_node(gateway=_FakeGateway())  # type: ignore[arg-type]
    result = await node(state)
    assert _unwrap(result)["sections_detected"] == 3


# ===========================================================================
# ingestion_traceability — primer emit
# ===========================================================================


async def test_traceability_emits_prompt_first_time() -> None:
    state = _state()
    state.suggested_classification = Classification(
        category="TEC",
        document_type="POL",
        confidence=0.9,
        reasoning="x",
    )
    node = make_ingestion_traceability_node()
    update = await node(state)
    upd = _unwrap(update)
    content = upd["messages"][0]["content"].lower()
    assert "aprob" in content  # "quién lo aprobó"
    assert "fuente original" in content
    assert upd["awaiting_confirmation"] == "ingest_meta"


async def test_traceability_errors_without_classification() -> None:
    state = _state()
    # suggested_classification es None
    node = make_ingestion_traceability_node()
    update = await node(state)
    upd = _unwrap(update)
    assert upd["last_error"] == "missing_classification"


# ===========================================================================
# ingestion_traceability — parsing
# ===========================================================================


def test_parse_traceability_full_input() -> None:
    raw = (
        "Aprobador: Camila Pereyra\n"
        "Fecha: 2026-05-15\n"
        "Fuente: https://sharepoint.sqa.co/policies/retention.docx\n"
        "Versión: 2.1"
    )
    t = _parse_traceability(raw)
    assert "Camila Pereyra" in t.approved_by
    assert t.approval_date == "2026-05-15"
    assert "sharepoint" in t.source_origin
    assert t.source_version == "2.1"


def test_parse_traceability_with_numbered_list() -> None:
    raw = (
        "1. Andrés Altamiranda\n"
        "2. 2026-05-23\n"
        "3. https://wiki.sqa.co/doc"
    )
    t = _parse_traceability(raw)
    assert "Andrés Altamiranda" in t.approved_by
    assert t.approval_date == "2026-05-23"
    assert "wiki.sqa.co" in t.source_origin


def test_parse_traceability_defaults_when_missing_fields() -> None:
    """Sin fecha ni URL → defaults razonables."""
    raw = "Aprobador: Juan Pérez"
    t = _parse_traceability(raw)
    assert "Juan Pérez" in t.approved_by
    # Fecha default: hoy
    assert len(t.approval_date) == 10
    assert t.source_origin == "no especificado"
    assert t.source_version is None


def test_parse_traceability_empty_input() -> None:
    t = _parse_traceability("")
    assert t.approved_by == "no especificado"


def test_parse_traceability_version_only() -> None:
    raw = "Juan\n2026-05-20\nv1.2.3"
    t = _parse_traceability(raw)
    assert t.source_version == "1.2.3"


# ===========================================================================
# ingestion_traceability — segundo turno (parse + Command)
# ===========================================================================


async def test_traceability_parses_and_chains_to_index() -> None:
    state = _state()
    state.suggested_classification = Classification(
        category="TEC", document_type="POL", confidence=0.9, reasoning="x"
    )
    state.awaiting_confirmation = "ingest_meta"
    _add_user(
        state,
        "Camila Pereyra\n2026-05-15\nhttps://sharepoint.sqa.co/doc.docx",
    )
    node = make_ingestion_traceability_node()
    result = await node(state)
    assert _goto(result) == "index_ingestion"
    upd = _unwrap(result)
    assert upd["traceability"].approved_by == "Camila Pereyra"
    assert upd["traceability"].approval_date == "2026-05-15"


async def test_traceability_asks_again_when_response_empty() -> None:
    state = _state()
    state.suggested_classification = Classification(
        category="TEC", document_type="POL", confidence=0.9, reasoning="x"
    )
    state.awaiting_confirmation = "ingest_meta"
    # No user msg agregado
    node = make_ingestion_traceability_node()
    update = await node(state)
    upd = _unwrap(update)
    assert upd["awaiting_confirmation"] == "ingest_meta"


# ===========================================================================
# index_ingestion
# ===========================================================================


def _ingestion_ready_state() -> AgentState:
    state = _state()
    state.suggested_classification = Classification(
        category="TEC",
        document_type="POL",
        confidence=0.9,
        reasoning="x",
    )
    state.extracted_text = "# Política\n\nContenido."
    state.sections_detected = 1
    state.traceability = Traceability(
        approved_by="Camila Pereyra",
        approval_date="2026-05-15",
        source_origin="https://sharepoint.sqa.co/doc",
        source_version="2.1",
    )
    return state


async def test_index_ingestion_creates_document_and_item() -> None:
    state = _ingestion_ready_state()
    doc_repo = _FakeDocRepo()
    ing_repo = _FakeIngestRepo()
    node = make_index_ingestion_node(
        document_repo=doc_repo,  # type: ignore[arg-type]
        ingestion_repo=ing_repo,  # type: ignore[arg-type]
    )
    update = await node(state)
    assert update["generated_document_id"] is not None
    assert update["ingestion_item_id"] is not None
    assert len(doc_repo.created) == 1
    assert len(ing_repo.created) == 1

    doc = doc_repo.created[0]
    assert doc.autoritativo is False
    assert doc.aprobador_name == "Camila Pereyra"
    assert doc.version == "2.1"

    item = ing_repo.created[0]
    assert item.aprobador_name == "Camila Pereyra"
    assert item.fuente_original == "https://sharepoint.sqa.co/doc"


async def test_index_ingestion_errors_without_classification() -> None:
    state = _ingestion_ready_state()
    state.suggested_classification = None
    doc_repo = _FakeDocRepo()
    ing_repo = _FakeIngestRepo()
    node = make_index_ingestion_node(
        document_repo=doc_repo,  # type: ignore[arg-type]
        ingestion_repo=ing_repo,  # type: ignore[arg-type]
    )
    update = await node(state)
    assert update["last_error"]
    assert doc_repo.created == []
    assert ing_repo.created == []


async def test_index_ingestion_errors_without_traceability() -> None:
    state = _ingestion_ready_state()
    state.traceability = None
    node = make_index_ingestion_node(
        document_repo=_FakeDocRepo(),  # type: ignore[arg-type]
        ingestion_repo=_FakeIngestRepo(),  # type: ignore[arg-type]
    )
    update = await node(state)
    assert update["last_error"]


async def test_index_ingestion_errors_when_doc_repo_fails() -> None:
    state = _ingestion_ready_state()
    doc_repo = _FakeDocRepo(should_fail=True)
    ing_repo = _FakeIngestRepo()
    node = make_index_ingestion_node(
        document_repo=doc_repo,  # type: ignore[arg-type]
        ingestion_repo=ing_repo,  # type: ignore[arg-type]
    )
    update = await node(state)
    assert update["last_error"]
    assert ing_repo.created == []  # no se persistió item si falló doc


async def test_index_ingestion_uses_markdown_heading_as_title() -> None:
    state = _ingestion_ready_state()
    state.extracted_text = "# Política de retención de datos\n\nContenido del doc."
    doc_repo = _FakeDocRepo()
    ing_repo = _FakeIngestRepo()
    node = make_index_ingestion_node(
        document_repo=doc_repo,  # type: ignore[arg-type]
        ingestion_repo=ing_repo,  # type: ignore[arg-type]
    )
    await node(state)
    assert doc_repo.created[0].titulo == "Política de retención de datos"


async def test_index_ingestion_falls_back_to_first_words_as_title() -> None:
    """Sin heading markdown, usa las primeras palabras."""
    state = _ingestion_ready_state()
    state.extracted_text = "Esta es una política sobre retención por noventa días sin heading."
    doc_repo = _FakeDocRepo()
    ing_repo = _FakeIngestRepo()
    node = make_index_ingestion_node(
        document_repo=doc_repo,  # type: ignore[arg-type]
        ingestion_repo=ing_repo,  # type: ignore[arg-type]
    )
    await node(state)
    assert "Esta es una política sobre retención por noventa" in doc_repo.created[0].titulo


async def test_index_ingestion_handles_traceability_without_version() -> None:
    """Si traceability.source_version es None, el doc se persiste con
    version='1.0' (porque NonEmptyStr no admite None)."""
    state = _ingestion_ready_state()
    state.traceability = Traceability(
        approved_by="X",
        approval_date="2026-05-15",
        source_origin="x",
        source_version=None,
    )
    doc_repo = _FakeDocRepo()
    ing_repo = _FakeIngestRepo()
    node = make_index_ingestion_node(
        document_repo=doc_repo,  # type: ignore[arg-type]
        ingestion_repo=ing_repo,  # type: ignore[arg-type]
    )
    await node(state)
    assert doc_repo.created[0].version == "1.0"


# ===========================================================================
# index_ingestion — hook indexer (Fase 3.6)
# ===========================================================================


@dataclass
class _FakeIndexer:
    """Fake mínimo del `Indexer` para verificar el hook."""

    calls: list[dict[str, Any]] = field(default_factory=list)
    should_fail: bool = False

    async def index_document(
        self, document_id: str, *, sections, text=None, replace=True  # type: ignore[no-untyped-def]
    ):
        self.calls.append(
            {
                "document_id": document_id,
                "sections": list(sections),
                "text": text,
                "replace": replace,
            }
        )
        if self.should_fail:
            raise RuntimeError("indexer down")
        from sqa_kb.rag.indexer import IndexerResult

        return IndexerResult(
            document_id=document_id,
            chunks_created=1,
            tokens_embedded=10,
            cost_usd=0.0001,
            sub_batches=1,
            replaced_old_chunks=0,
        )


async def test_index_ingestion_calls_indexer_with_extracted_text() -> None:
    """Hook RAG: chunkea el `state.extracted_text` como Section."""
    state = _ingestion_ready_state()
    indexer = _FakeIndexer()
    node = make_index_ingestion_node(
        document_repo=_FakeDocRepo(),  # type: ignore[arg-type]
        ingestion_repo=_FakeIngestRepo(),  # type: ignore[arg-type]
        indexer=indexer,  # type: ignore[arg-type]
    )
    update = await node(state)

    assert update["generated_document_id"] is not None
    assert len(indexer.calls) == 1
    call = indexer.calls[0]
    assert call["document_id"] == update["generated_document_id"]
    # Sections con el texto extraído.
    assert len(call["sections"]) == 1
    section = call["sections"][0]
    assert section.content == state.extracted_text


async def test_index_ingestion_no_indexer_no_op() -> None:
    """Sin indexer (back-compat), el nodo no intenta indexar."""
    state = _ingestion_ready_state()
    node = make_index_ingestion_node(
        document_repo=_FakeDocRepo(),  # type: ignore[arg-type]
        ingestion_repo=_FakeIngestRepo(),  # type: ignore[arg-type]
        # sin indexer
    )
    update = await node(state)
    assert update["generated_document_id"] is not None
    assert update["current_stage"] == "index_ingestion"


async def test_index_ingestion_indexer_failure_does_not_break_response() -> None:
    """Si el indexer falla, el flujo del agente igual cierra OK."""
    state = _ingestion_ready_state()
    indexer = _FakeIndexer(should_fail=True)
    node = make_index_ingestion_node(
        document_repo=_FakeDocRepo(),  # type: ignore[arg-type]
        ingestion_repo=_FakeIngestRepo(),  # type: ignore[arg-type]
        indexer=indexer,  # type: ignore[arg-type]
    )
    update = await node(state)

    # El doc + item se crearon, el response salió.
    assert update["generated_document_id"] is not None
    assert update["ingestion_item_id"] is not None
    assert update["current_stage"] == "index_ingestion"
    # El indexer fue intentado.
    assert len(indexer.calls) == 1


async def test_index_ingestion_does_not_index_when_persistence_fails() -> None:
    """Si persistir el Document falla, NO se intenta indexar."""
    state = _ingestion_ready_state()
    indexer = _FakeIndexer()
    node = make_index_ingestion_node(
        document_repo=_FakeDocRepo(should_fail=True),  # type: ignore[arg-type]
        ingestion_repo=_FakeIngestRepo(),  # type: ignore[arg-type]
        indexer=indexer,  # type: ignore[arg-type]
    )
    update = await node(state)
    assert update["last_error"]
    # No tiene sentido indexar si el Document no se persistió.
    assert indexer.calls == []
