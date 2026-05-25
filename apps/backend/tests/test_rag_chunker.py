"""Tests del Chunker (Fase 3.1) — 4 estrategias por tipo de documento.

Cubre cada estrategia:
- semantic: respeta splits naturales, overlap, configs por tipo.
- by_steps (INST): cada paso → chunk, oversized cae a semantic interno.
- hierarchical (ARCL): preserva el path en section_title.
- per_slide (PRES): slide_number en metadata.

Edge cases:
- Section empty content → skip.
- Sin sections + sin text → []
- Sin sections + text fallback.
- Tipo desconocido → fallback config conservador.
- chunk_index monotónico.
- count_tokens helper independiente.
"""

from __future__ import annotations

from sqa_kb.rag.chunker import (
    CHUNK_CONFIG,
    Chunk,
    Chunker,
    Section,
    count_tokens,
)

# ===========================================================================
# count_tokens
# ===========================================================================


def test_count_tokens_zero_for_empty() -> None:
    assert count_tokens("") == 0


def test_count_tokens_increases_with_length() -> None:
    short = count_tokens("Hola")
    long = count_tokens("Hola mundo. " * 50)
    assert long > short


def test_count_tokens_handles_unicode() -> None:
    """Caracteres con acentos no rompen el tokenizer."""
    assert count_tokens("ñoño y técnica") > 0


def test_count_tokens_handles_emoji() -> None:
    """Emojis no rompen tiktoken (raros en KB pero defensivo)."""
    assert count_tokens("emoji 🚀 test") > 0


# ===========================================================================
# CHUNK_CONFIG sanity
# ===========================================================================


def test_config_covers_all_11_doc_types() -> None:
    """Todos los tipos del playbook deben tener config."""
    expected = {
        "POL", "PROC", "GUIA", "INST", "SERV",
        "MTEC", "ACEL", "UEN", "ARCL", "FORM", "PRES",
    }
    assert expected.issubset(CHUNK_CONFIG.keys())


def test_config_strategies_match_roadmap() -> None:
    """Sanity: las estrategias coinciden con el §17.2."""
    assert CHUNK_CONFIG["INST"].strategy == "by_steps"
    assert CHUNK_CONFIG["ARCL"].strategy == "hierarchical"
    assert CHUNK_CONFIG["PRES"].strategy == "per_slide"
    assert CHUNK_CONFIG["POL"].strategy == "semantic"


def test_config_overlap_never_exceeds_target() -> None:
    """Edge: overlap > target produce loops infinitos en el splitter."""
    for cfg in CHUNK_CONFIG.values():
        assert cfg.overlap_tokens < cfg.target_size_tokens


# ===========================================================================
# Empty inputs
# ===========================================================================


def test_chunk_empty_sections_returns_empty() -> None:
    chunker = Chunker()
    out = chunker.chunk(doc_type="POL", sections=[])
    assert out == []


def test_chunk_empty_text_fallback_returns_empty() -> None:
    chunker = Chunker()
    out = chunker.chunk(doc_type="POL", sections=[], text="")
    assert out == []


def test_chunk_whitespace_text_returns_empty() -> None:
    chunker = Chunker()
    out = chunker.chunk(doc_type="POL", sections=[], text="   \n\t  ")
    assert out == []


def test_chunk_text_fallback_with_no_sections() -> None:
    """Legacy: extracción sin headings detectados → 1 sección con todo el texto."""
    chunker = Chunker()
    out = chunker.chunk(
        doc_type="POL",
        sections=[],
        text="Política institucional de captura de conocimiento.",
    )
    assert len(out) == 1
    assert "Política institucional" in out[0].content


def test_chunk_skips_section_with_empty_content() -> None:
    chunker = Chunker()
    sections = [
        Section(title="Vacía", content=""),
        Section(title="Con texto", content="Hola mundo del KB."),
    ]
    out = chunker.chunk(doc_type="POL", sections=sections)
    assert len(out) == 1
    assert out[0].section_title == "Con texto"


# ===========================================================================
# Estrategia semantic (POL/PROC/GUIA/SERV/MTEC/ACEL/UEN/FORM)
# ===========================================================================


def test_semantic_produces_chunks_with_index_monotonic() -> None:
    chunker = Chunker()
    sections = [
        Section(title="A", content="Texto sección A. " * 50),
        Section(title="B", content="Texto sección B. " * 50),
    ]
    out = chunker.chunk(doc_type="POL", sections=sections)
    assert len(out) >= 2
    # chunk_index debe ser 0, 1, 2, ...
    indexes = [c.chunk_index for c in out]
    assert indexes == list(range(len(out)))


def test_semantic_short_section_produces_one_chunk() -> None:
    chunker = Chunker()
    sections = [Section(title="Corta", content="Una frase corta.")]
    out = chunker.chunk(doc_type="POL", sections=sections)
    assert len(out) == 1
    assert out[0].section_title == "Corta"
    assert out[0].metadata == {"strategy": "semantic"}


def test_semantic_splits_long_section() -> None:
    """Sección que excede el target debe partirse en varios chunks."""
    chunker = Chunker()
    # ~4000 chars de texto realista → varios chunks con target POL 700 tokens.
    long_text = (
        "Esta es una oración larga sobre captura de conocimiento. " * 80
    )
    sections = [Section(title="Larga", content=long_text)]
    out = chunker.chunk(doc_type="POL", sections=sections)
    assert len(out) >= 2


def test_semantic_chunks_have_token_count() -> None:
    chunker = Chunker()
    out = chunker.chunk(
        doc_type="POL",
        sections=[Section(title="X", content="Hola mundo del KB.")],
    )
    assert out[0].token_count > 0


def test_semantic_section_title_none_becomes_none() -> None:
    """Section sin title → section_title del chunk queda None (no string vacío)."""
    chunker = Chunker()
    out = chunker.chunk(
        doc_type="POL",
        sections=[Section(title="", content="Texto sin título.")],
    )
    assert out[0].section_title is None


# ===========================================================================
# Estrategia by_steps (INST)
# ===========================================================================


def test_by_steps_one_chunk_per_section() -> None:
    chunker = Chunker()
    sections = [
        Section(title="Paso 1", content="Verificar entorno."),
        Section(title="Paso 2", content="Ejecutar comando."),
        Section(title="Paso 3", content="Validar resultado."),
    ]
    out = chunker.chunk(doc_type="INST", sections=sections)
    assert len(out) == 3
    assert [c.section_title for c in out] == ["Paso 1", "Paso 2", "Paso 3"]
    assert all(c.metadata["strategy"] == "by_steps" for c in out)


def test_by_steps_oversized_step_falls_back_to_semantic() -> None:
    """Paso muy largo (excede max_size_tokens=400 para INST) → split semantic."""
    chunker = Chunker()
    huge_step = "Este paso es enorme. " * 200  # >> 400 tokens
    sections = [
        Section(title="Paso enorme", content=huge_step),
        Section(title="Paso normal", content="Corto."),
    ]
    out = chunker.chunk(doc_type="INST", sections=sections)
    # El paso enorme se divide; el normal sigue siendo 1 chunk.
    assert len(out) >= 3
    # El paso enorme tiene metadata oversized_split=True.
    oversized = [c for c in out if c.metadata.get("oversized_split")]
    assert len(oversized) >= 1


def test_by_steps_skips_empty_step() -> None:
    chunker = Chunker()
    sections = [
        Section(title="Paso 1", content="Algo."),
        Section(title="Paso 2", content=""),  # vacío → skip
        Section(title="Paso 3", content="Otra cosa."),
    ]
    out = chunker.chunk(doc_type="INST", sections=sections)
    assert len(out) == 2
    assert [c.section_title for c in out] == ["Paso 1", "Paso 3"]


# ===========================================================================
# Estrategia hierarchical (ARCL)
# ===========================================================================


def test_hierarchical_includes_path_in_section_title() -> None:
    chunker = Chunker()
    sections = [
        Section(
            title="Necesidades",
            content="El cliente requiere automatización.",
            path=("Arquetipo Enterprise", "Perfil ejecutivo"),
        ),
    ]
    out = chunker.chunk(doc_type="ARCL", sections=sections)
    assert len(out) == 1
    assert out[0].section_title == "Arquetipo Enterprise > Perfil ejecutivo > Necesidades"


def test_hierarchical_without_path_uses_title_only() -> None:
    chunker = Chunker()
    sections = [Section(title="Cliente A", content="Descripción del cliente.")]
    out = chunker.chunk(doc_type="ARCL", sections=sections)
    assert out[0].section_title == "Cliente A"


def test_hierarchical_metadata_includes_path() -> None:
    chunker = Chunker()
    sections = [
        Section(
            title="X",
            content="contenido",
            path=("Padre", "Hijo"),
        ),
    ]
    out = chunker.chunk(doc_type="ARCL", sections=sections)
    assert out[0].metadata["path"] == ["Padre", "Hijo"]
    assert out[0].metadata["strategy"] == "hierarchical"


def test_hierarchical_oversized_section_splits_keeping_full_title() -> None:
    chunker = Chunker()
    huge = "Texto largo del cliente. " * 200  # > max 900 tokens de ARCL
    sections = [
        Section(
            title="Sub-perfil",
            content=huge,
            path=("Enterprise",),
        ),
    ]
    out = chunker.chunk(doc_type="ARCL", sections=sections)
    assert len(out) >= 2
    # Todos los sub-chunks mantienen el full title.
    for c in out:
        assert c.section_title == "Enterprise > Sub-perfil"
        assert c.metadata.get("oversized_split") is True


# ===========================================================================
# Estrategia per_slide (PRES)
# ===========================================================================


def test_per_slide_one_chunk_per_section() -> None:
    chunker = Chunker()
    sections = [
        Section(title="Portada", content="Título principal."),
        Section(title="Agenda", content="1. Intro 2. Detalle 3. Cierre"),
        Section(title="Cierre", content="Gracias."),
    ]
    out = chunker.chunk(doc_type="PRES", sections=sections)
    assert len(out) == 3
    # slide_number monotónico en metadata
    assert [c.metadata["slide_number"] for c in out] == [1, 2, 3]


def test_per_slide_assigns_default_title_when_missing() -> None:
    """Slide sin title → `Slide N`."""
    chunker = Chunker()
    sections = [
        Section(title="", content="contenido slide 1"),
        Section(title="Con título", content="contenido slide 2"),
    ]
    out = chunker.chunk(doc_type="PRES", sections=sections)
    assert out[0].section_title == "Slide 1"
    assert out[1].section_title == "Con título"


def test_per_slide_oversized_slide_falls_to_semantic() -> None:
    """Slide muy larga (raro en PRES pero defensivo)."""
    chunker = Chunker()
    huge_slide = "Mucho texto en una sola slide. " * 200
    sections = [Section(title="Slide larga", content=huge_slide)]
    out = chunker.chunk(doc_type="PRES", sections=sections)
    assert len(out) >= 2
    assert all(c.section_title == "Slide larga" for c in out)
    assert any(c.metadata.get("oversized_split") for c in out)


def test_per_slide_skips_empty_slide() -> None:
    chunker = Chunker()
    sections = [
        Section(title="S1", content="x"),
        Section(title="S2", content=""),
        Section(title="S3", content="y"),
    ]
    out = chunker.chunk(doc_type="PRES", sections=sections)
    assert len(out) == 2


# ===========================================================================
# Tipo desconocido → fallback
# ===========================================================================


def test_unknown_doc_type_uses_default_config() -> None:
    chunker = Chunker()
    out = chunker.chunk(
        doc_type="NEW_TYPE_FUTURO",  # type: ignore[arg-type]
        sections=[Section(title="X", content="Texto.")],
    )
    assert len(out) == 1
    # Default strategy: semantic
    assert out[0].metadata["strategy"] == "semantic"


# ===========================================================================
# Chunk dataclass sanity
# ===========================================================================


def test_chunk_is_frozen() -> None:
    """Sanity: el dataclass es inmutable (slots+frozen)."""
    import pytest

    c = Chunk(content="x", section_title=None, token_count=1, chunk_index=0)
    with pytest.raises((AttributeError, Exception)):
        c.content = "modificado"  # type: ignore[misc]


def test_chunk_default_metadata_is_independent() -> None:
    """Default factory: dos instancias no comparten dict mutable."""
    a = Chunk(content="A", section_title=None, token_count=1, chunk_index=0)
    b = Chunk(content="B", section_title=None, token_count=1, chunk_index=1)
    a.metadata["key"] = "value"
    assert "key" not in b.metadata
