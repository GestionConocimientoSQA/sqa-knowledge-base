"""Chunker — divide un documento en piezas indexables (Fase 3.1).

Cuatro estrategias (ROADMAP §17.2):
- **semantic** (default): `RecursiveCharacterTextSplitter` con configs
  por tipo. Respeta saltos de párrafo / línea / palabra en ese orden.
- **by_steps** (INST): cada paso → 1 chunk. Pensado para instructivos
  donde el orden importa más que la longitud.
- **hierarchical** (ARCL): preserva la jerarquía título → contenido.
  Cada hijo guarda su path completo (`Padre > Hijo`).
- **per_slide** (PRES): cada slide → 1 chunk. Pensado para presentaciones.

El chunker recibe `Section`s (no texto crudo) — el extractor de Fase 4
les pasa título + contenido por cada heading detectado. Si solo hay
texto plano (legacy), una sola Section con `title=""` y todo el texto
adentro alcanza.

Conteo de tokens: usamos `tiktoken` con encoding `cl100k_base`. Es la
referencia estándar de la industria — Cohere no expone su tokenizer
público en el SDK Python, y la aproximación con cl100k_base difiere
< 5% en español según mediciones de la comunidad. Adecuado para
chunking (no necesitamos precisión exacta).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any, Literal

import tiktoken
from langchain_text_splitters import RecursiveCharacterTextSplitter

ChunkStrategy = Literal["semantic", "by_steps", "hierarchical", "per_slide"]


# ===========================================================================
# Configs por tipo de documento (§17.2 ROADMAP)
# ===========================================================================


@dataclass(frozen=True, slots=True)
class ChunkConfig:
    """Config de chunking para un tipo de documento.

    `target_size_tokens` es el objetivo del splitter; chunks reales suelen
    quedar entre 80% y 100% del target. `max_size_tokens` es el techo
    duro — si un chunk lo excede, el splitter lo divide.
    """

    target_size_tokens: int
    max_size_tokens: int
    overlap_tokens: int
    strategy: ChunkStrategy


# Configs por tipo. `target/max/overlap` espejo del §17.2.
CHUNK_CONFIG: dict[str, ChunkConfig] = {
    "POL": ChunkConfig(700, 800, 80, "semantic"),
    "PROC": ChunkConfig(600, 700, 80, "semantic"),
    "GUIA": ChunkConfig(700, 800, 80, "semantic"),
    "INST": ChunkConfig(300, 400, 40, "by_steps"),
    "SERV": ChunkConfig(900, 1000, 100, "semantic"),
    "MTEC": ChunkConfig(500, 600, 60, "semantic"),
    "ACEL": ChunkConfig(700, 800, 80, "semantic"),
    "UEN": ChunkConfig(900, 1000, 100, "semantic"),
    "ARCL": ChunkConfig(800, 900, 100, "hierarchical"),
    "FORM": ChunkConfig(500, 600, 50, "semantic"),
    "PRES": ChunkConfig(400, 500, 40, "per_slide"),
}

# Fallback para tipos no listados (futuro): semantic conservador.
_DEFAULT_CONFIG = ChunkConfig(600, 700, 60, "semantic")


# ===========================================================================
# Dataclasses de entrada y salida
# ===========================================================================


@dataclass(frozen=True, slots=True)
class Section:
    """Trozo del documento con título + contenido.

    `path` es la jerarquía completa hasta esta sección (p.ej.
    `["Capítulo 1", "1.1 Subtema"]`). Útil para `hierarchical`.
    """

    title: str
    content: str
    path: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class Chunk:
    """Pieza indexable.

    `content` es el texto plano del chunk SIN el header contextual
    (`format_context_header` lo agrega solo para embed).
    `metadata` queda libre — el indexer puede meter `doc_type`,
    `section_path`, etc. para queries filtradas.
    """

    content: str
    section_title: str | None
    token_count: int
    chunk_index: int
    metadata: dict[str, Any] = field(default_factory=dict)


# ===========================================================================
# Tokenizer compartido
# ===========================================================================


# tiktoken cachea el encoding internamente. Lo cargamos lazy + module-level.
_ENCODER = tiktoken.get_encoding("cl100k_base")


def count_tokens(text: str) -> int:
    """Cuenta tokens del texto con cl100k_base."""
    if not text:
        return 0
    return len(_ENCODER.encode(text, disallowed_special=()))


# ===========================================================================
# Chunker
# ===========================================================================


class Chunker:
    """Stateless. Recibe sections + doc_type, devuelve `list[Chunk]`."""

    def chunk(
        self,
        *,
        doc_type: str,
        sections: Sequence[Section],
        text: str | None = None,
    ) -> list[Chunk]:
        """Decide la estrategia según `doc_type` y delega al método
        correspondiente.

        `text` solo se usa como fallback cuando `sections` está vacío
        (legacy / extracción que no detectó headings).
        """
        config = CHUNK_CONFIG.get(doc_type, _DEFAULT_CONFIG)

        normalized_sections = self._fallback_to_single_section(sections, text)
        if not normalized_sections:
            return []

        if config.strategy == "by_steps":
            return self._chunk_by_steps(normalized_sections, config)
        if config.strategy == "hierarchical":
            return self._chunk_hierarchical(normalized_sections, config)
        if config.strategy == "per_slide":
            return self._chunk_per_slide(normalized_sections, config)
        # default: semantic
        return self._chunk_semantic(normalized_sections, config)

    # ===========================================================================
    # Strategies
    # ===========================================================================

    def _chunk_semantic(
        self, sections: Sequence[Section], config: ChunkConfig
    ) -> list[Chunk]:
        """Divide cada sección con `RecursiveCharacterTextSplitter`.

        El splitter trabaja en chars; convertimos `target_size_tokens` a
        chars usando ratio 1 token ≈ 4 chars (regla típica en español).
        Luego validamos `token_count` real con tiktoken al construir el
        chunk — si excede `max_size_tokens` igual lo incluimos (sería
        excepcional y romper el flujo ahí sería peor).
        """
        chars_per_token = 4
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=config.target_size_tokens * chars_per_token,
            chunk_overlap=config.overlap_tokens * chars_per_token,
            separators=["\n\n", "\n", ". ", " ", ""],
        )

        chunks: list[Chunk] = []
        chunk_idx = 0
        for section in sections:
            if not section.content.strip():
                continue
            for piece in splitter.split_text(section.content):
                cleaned = piece.strip()
                if not cleaned:
                    continue
                chunks.append(
                    Chunk(
                        content=cleaned,
                        section_title=section.title or None,
                        token_count=count_tokens(cleaned),
                        chunk_index=chunk_idx,
                        metadata={"strategy": "semantic"},
                    )
                )
                chunk_idx += 1
        return chunks

    def _chunk_by_steps(
        self, sections: Sequence[Section], config: ChunkConfig
    ) -> list[Chunk]:
        """Cada sección representa un paso. Si una sección excede el max,
        se rompe semánticamente para no perder contenido."""
        chunks: list[Chunk] = []
        chunk_idx = 0
        for section in sections:
            cleaned = section.content.strip()
            if not cleaned:
                continue
            tokens = count_tokens(cleaned)
            if tokens <= config.max_size_tokens:
                chunks.append(
                    Chunk(
                        content=cleaned,
                        section_title=section.title or None,
                        token_count=tokens,
                        chunk_index=chunk_idx,
                        metadata={"strategy": "by_steps"},
                    )
                )
                chunk_idx += 1
            else:
                # Paso sobredimensionado → cae a semantic dentro de ese paso.
                sub_chunks = self._chunk_semantic([section], config)
                for sub in sub_chunks:
                    chunks.append(
                        Chunk(
                            content=sub.content,
                            section_title=sub.section_title,
                            token_count=sub.token_count,
                            chunk_index=chunk_idx,
                            metadata={"strategy": "by_steps", "oversized_split": True},
                        )
                    )
                    chunk_idx += 1
        return chunks

    def _chunk_hierarchical(
        self, sections: Sequence[Section], config: ChunkConfig
    ) -> list[Chunk]:
        """Cada sección produce un chunk. `section_title` incluye el path
        ancestral (`Padre > Hijo`) para preservar jerarquía en el embed."""
        chunks: list[Chunk] = []
        chunk_idx = 0
        for section in sections:
            cleaned = section.content.strip()
            if not cleaned:
                continue
            full_title = (
                " > ".join([*section.path, section.title])
                if section.path
                else section.title
            )
            tokens = count_tokens(cleaned)
            if tokens <= config.max_size_tokens:
                chunks.append(
                    Chunk(
                        content=cleaned,
                        section_title=full_title or None,
                        token_count=tokens,
                        chunk_index=chunk_idx,
                        metadata={
                            "strategy": "hierarchical",
                            "path": list(section.path),
                        },
                    )
                )
                chunk_idx += 1
            else:
                # Sección demasiado larga → semantic split, manteniendo
                # el full_title como section_title para todos los pedazos.
                semantic_parts = self._chunk_semantic([section], config)
                for sub in semantic_parts:
                    chunks.append(
                        Chunk(
                            content=sub.content,
                            section_title=full_title or None,
                            token_count=sub.token_count,
                            chunk_index=chunk_idx,
                            metadata={
                                "strategy": "hierarchical",
                                "path": list(section.path),
                                "oversized_split": True,
                            },
                        )
                    )
                    chunk_idx += 1
        return chunks

    def _chunk_per_slide(
        self, sections: Sequence[Section], config: ChunkConfig
    ) -> list[Chunk]:
        """Una sección = una slide = un chunk. Si una slide excede el max
        (raro en presentaciones), cae a semantic."""
        chunks: list[Chunk] = []
        chunk_idx = 0
        for slide_idx, section in enumerate(sections, start=1):
            cleaned = section.content.strip()
            if not cleaned:
                continue
            tokens = count_tokens(cleaned)
            slide_title = section.title or f"Slide {slide_idx}"
            if tokens <= config.max_size_tokens:
                chunks.append(
                    Chunk(
                        content=cleaned,
                        section_title=slide_title,
                        token_count=tokens,
                        chunk_index=chunk_idx,
                        metadata={"strategy": "per_slide", "slide_number": slide_idx},
                    )
                )
                chunk_idx += 1
            else:
                sub_chunks = self._chunk_semantic([section], config)
                for sub in sub_chunks:
                    chunks.append(
                        Chunk(
                            content=sub.content,
                            section_title=slide_title,
                            token_count=sub.token_count,
                            chunk_index=chunk_idx,
                            metadata={
                                "strategy": "per_slide",
                                "slide_number": slide_idx,
                                "oversized_split": True,
                            },
                        )
                    )
                    chunk_idx += 1
        return chunks

    # ===========================================================================
    # Helpers
    # ===========================================================================

    def _fallback_to_single_section(
        self, sections: Sequence[Section], text: str | None
    ) -> list[Section]:
        """Si no nos pasaron sections (extractor sin headings detectados),
        construimos una única Section con el texto completo."""
        if sections:
            return list(sections)
        if text and text.strip():
            return [Section(title="", content=text)]
        return []
