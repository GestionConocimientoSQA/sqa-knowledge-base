"""Tests del header contextual."""

from __future__ import annotations

from sqa_kb.rag.context_header import format_context_header, type_human_name


def test_header_with_all_fields() -> None:
    out = format_context_header(
        document_type="MTEC",
        category="TEC",
        section_title="Configuración de Healenium",
        content="Para configurar Healenium...",
    )
    expected_prefix = (
        "[Tipo: Memoria Técnica | Carpeta: TEC "
        "| Sección: Configuración de Healenium]"
    )
    assert out.startswith(expected_prefix)
    assert "Para configurar Healenium..." in out
    # El header va separado del contenido por \n\n
    assert "]\n\nPara" in out


def test_header_omits_section_when_none() -> None:
    out = format_context_header(
        document_type="POL",
        category="ARQ",
        section_title=None,
        content="texto",
    )
    assert "Sección:" not in out
    assert "[Tipo: Política | Carpeta: ARQ]" in out


def test_header_omits_section_when_empty_string() -> None:
    out = format_context_header(
        document_type="POL",
        category="ARQ",
        section_title="",
        content="texto",
    )
    assert "Sección:" not in out


def test_header_omits_section_when_whitespace_only() -> None:
    out = format_context_header(
        document_type="POL",
        category="ARQ",
        section_title="   \n",
        content="texto",
    )
    assert "Sección:" not in out


def test_header_strips_section_title() -> None:
    out = format_context_header(
        document_type="POL",
        category="ARQ",
        section_title="  con espacios  ",
        content="x",
    )
    assert "Sección: con espacios]" in out


def test_unknown_type_falls_back_to_code() -> None:
    """Tipo nuevo (futuro) → usa el código tal cual, no rompe el indexer."""
    out = format_context_header(
        document_type="FUTURE-TYPE",
        category="TEC",
        content="x",
    )
    assert "Tipo: FUTURE-TYPE" in out


def test_type_human_name_returns_translation() -> None:
    assert type_human_name("MTEC") == "Memoria Técnica"
    assert type_human_name("POL") == "Política"
    assert type_human_name("ARCL") == "Arquetipo de Cliente"


def test_type_human_name_unknown_returns_input() -> None:
    assert type_human_name("UNKNOWN") == "UNKNOWN"


def test_header_preserves_unicode_in_section() -> None:
    out = format_context_header(
        document_type="MTEC",
        category="TEC",
        section_title="Configuración técnica del módulo ñandú",
        content="...",
    )
    assert "ñandú" in out
    assert "técnica" in out


def test_header_preserves_content_unchanged() -> None:
    """El contenido (post-header) debe pasar intacto."""
    content = "Línea 1\nLínea 2\n\nPárrafo 2"
    out = format_context_header(
        document_type="POL",
        category="TEC",
        content=content,
    )
    # El header termina con \n\n, después viene el content tal cual.
    assert out.endswith(content)
