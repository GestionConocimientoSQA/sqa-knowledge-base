"""Tests del módulo de branding SQA (Fase 4.0)."""

from __future__ import annotations

import pytest

from sqa_kb.documents import branding
from sqa_kb.documents.branding import RgbColor, category_color

# ===========================================================================
# RgbColor
# ===========================================================================


def test_rgb_color_valid_hex() -> None:
    c = RgbColor("03277D")
    assert c.hex == "03277D"
    assert c.with_hash == "#03277D"


def test_rgb_color_rgb_tuple() -> None:
    c = RgbColor("FB9E13")  # naranja SQA
    assert c.rgb_tuple == (251, 158, 19)


def test_rgb_color_rgb_tuple_black_and_white() -> None:
    assert RgbColor("000000").rgb_tuple == (0, 0, 0)
    assert RgbColor("FFFFFF").rgb_tuple == (255, 255, 255)


def test_rgb_color_rejects_hash_prefix() -> None:
    with pytest.raises(ValueError, match="hex inválido"):
        RgbColor("#03277D")


def test_rgb_color_rejects_short_hex() -> None:
    with pytest.raises(ValueError, match="hex inválido"):
        RgbColor("FFF")


def test_rgb_color_rejects_non_hex_chars() -> None:
    with pytest.raises(ValueError, match="hex inválido"):
        RgbColor("GGGGGG")


def test_rgb_color_is_frozen() -> None:
    from dataclasses import FrozenInstanceError

    c = RgbColor("03277D")
    with pytest.raises(FrozenInstanceError):
        c.hex = "000000"  # type: ignore[misc]


def test_rgb_color_accepts_lowercase_hex() -> None:
    c = RgbColor("fb9e13")
    assert c.rgb_tuple == (251, 158, 19)


# ===========================================================================
# Paleta — valores derivados del frontend
# ===========================================================================


def test_palette_matches_frontend_hsl_derivation() -> None:
    """Los hex provienen de las HSL de globals.css. Smoke de los 3
    colores que firman la identidad SQA."""
    assert branding.AZUL_CORP.hex == "03277D"  # 222 96% 25%
    assert branding.NARANJA.hex == "FB9E13"  # 36 97% 53%
    assert branding.INK.hex == "080D26"  # 231 65% 9%


def test_semantic_roles_alias_real_colors() -> None:
    """Los roles semánticos apuntan a colores de la paleta (no hex sueltos)."""
    assert branding.COLOR_TITULO is branding.AZUL_CORP
    assert branding.COLOR_ACENTO is branding.NARANJA
    assert branding.COLOR_CUERPO is branding.INK


# ===========================================================================
# Tipografía
# ===========================================================================


def test_fonts_defined() -> None:
    assert branding.FONT_DISPLAY == "Exo 2"
    assert branding.FONT_BODY == "Montserrat"
    assert branding.FONT_MONO == "JetBrains Mono"


def test_type_scale_is_descending() -> None:
    """La escala tipográfica respeta jerarquía: portada > h1 > h2 > h3 > body."""
    assert (
        branding.SIZE_PORTADA_TITULO
        > branding.SIZE_H1
        > branding.SIZE_H2
        > branding.SIZE_H3
        >= branding.SIZE_BODY
        > branding.SIZE_CAPTION
        >= branding.SIZE_FOOTER
    )


# ===========================================================================
# category_color
# ===========================================================================


def test_category_color_known_categories() -> None:
    for code in ("PROC", "TEC", "ARQ", "HERR", "NEG", "ENV", "EST", "CONT"):
        color = category_color(code)
        assert isinstance(color, RgbColor)
        # Cada uno es parseable a RGB.
        assert len(color.rgb_tuple) == 3


def test_category_color_unknown_falls_back_to_ink() -> None:
    assert category_color("NOEXISTE") is branding.INK
    assert category_color("") is branding.INK


# ===========================================================================
# Metadata corporativa
# ===========================================================================


def test_org_metadata() -> None:
    assert branding.ORG_NAME == "SQA"
    assert "SQA" in branding.ORG_FULL_NAME
    assert "SQA" in branding.DOC_FOOTER_LEFT
