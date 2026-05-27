"""Branding SQA — paleta + tipografía + helpers de estilo (Fase 4.0).

Fuente de verdad de los colores: `apps/frontend/src/app/globals.css`
(variables `--sqa-*` en HSL). Acá las exponemos en **hex RGB** porque
`python-docx`/`python-pptx`/`reportlab` trabajan con RGB, no HSL.

Los valores hex fueron derivados de las HSL del frontend con
`colorsys.hls_to_rgb` para mantener un único origen visual entre la web
y los documentos generados. Si el frontend cambia la paleta, hay que
recomputar estos hex (ver el docstring de cada constante con la HSL
original).

Tipografía: las fuentes reales (Exo 2, Montserrat, JetBrains Mono) se
declaran por nombre. `python-docx`/`pptx` referencian la fuente por
nombre y el visor (Word/PowerPoint) la resuelve si está instalada; si
no, cae al fallback. NO embebemos los archivos de fuente en esta fase
(la incrustación de fuentes es un paso de hardening de Fase 10).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RgbColor:
    """Color RGB inmutable. `hex` sin `#` para interoperar con las libs
    de Office (que esperan `RGBColor.from_string('03277D')`)."""

    hex: str

    def __post_init__(self) -> None:
        if len(self.hex) != 6 or any(c not in "0123456789ABCDEFabcdef" for c in self.hex):
            raise ValueError(f"hex inválido: {self.hex!r} (esperado 6 dígitos sin '#')")

    @property
    def rgb_tuple(self) -> tuple[int, int, int]:
        """(R, G, B) en 0-255 — útil para reportlab (`colors.Color`)."""
        return (
            int(self.hex[0:2], 16),
            int(self.hex[2:4], 16),
            int(self.hex[4:6], 16),
        )

    @property
    def with_hash(self) -> str:
        return f"#{self.hex}"


# ===========================================================================
# Paleta SQA (derivada de las HSL de globals.css)
# ===========================================================================
#
# HSL original (frontend) → hex (este módulo):
#   azul-claro        204 67% 62%   → 5DABDF
#   azul-medio-claro  202 100% 43%  → 008BDB
#   azul-medio        211 100% 36%  → 0059B8
#   azul-oscuro       212 100% 14%  → 002147
#   azul-corp         222 96% 25%   → 03277D
#   azul-bright       225 100% 33%  → 002AA8
#   ink               231 65% 9%    → 080D26
#   naranja           36 97% 53%    → FB9E13
#   naranja-soft      41 100% 63%   → FFC342
#   amarillo          40 96% 64%    → FBC14B

AZUL_CLARO = RgbColor("5DABDF")
AZUL_MEDIO_CLARO = RgbColor("008BDB")
AZUL_MEDIO = RgbColor("0059B8")
AZUL_OSCURO = RgbColor("002147")
AZUL_CORP = RgbColor("03277D")
AZUL_BRIGHT = RgbColor("002AA8")
INK = RgbColor("080D26")
NARANJA = RgbColor("FB9E13")
NARANJA_SOFT = RgbColor("FFC342")
AMARILLO = RgbColor("FBC14B")

# Neutros para texto/fondos en documentos.
BLANCO = RgbColor("FFFFFF")
GRIS_TEXTO = RgbColor("3A4252")
GRIS_CLARO = RgbColor("F0F2F5")

# ---------------------------------------------------------------------------
# Roles semánticos — los generadores usan estos alias (no los hex crudos)
# para que un cambio de paleta no obligue a tocar cada generador.
# ---------------------------------------------------------------------------

COLOR_TITULO = AZUL_CORP
"""Títulos H1/portada."""
COLOR_SUBTITULO = AZUL_MEDIO
"""Headings H2/H3."""
COLOR_ACENTO = NARANJA
"""Subrayados, barras, viñetas destacadas (la firma visual de SQA)."""
COLOR_CUERPO = INK
"""Texto de párrafo."""
COLOR_TEXTO_SECUNDARIO = GRIS_TEXTO
"""Metadata, pies de página, captions."""
COLOR_FONDO_TABLA_HEADER = AZUL_CORP
"""Header de tablas (texto en blanco encima)."""
COLOR_FONDO_BANDA = GRIS_CLARO
"""Bandas/zebra striping en tablas y bloques de metadata."""


# ===========================================================================
# Tipografía
# ===========================================================================

FONT_DISPLAY = "Exo 2"
"""Títulos y portada. Fallback del visor: Montserrat → sans-serif."""
FONT_BODY = "Montserrat"
"""Texto de cuerpo."""
FONT_MONO = "JetBrains Mono"
"""Bloques de código / valores monoespaciados."""

FONT_FALLBACK_DISPLAY = "Calibri"
"""Fallback explícito si Exo 2 no está instalada (Word usa esto)."""
FONT_FALLBACK_BODY = "Calibri"


# ===========================================================================
# Tamaños (en puntos) — escala tipográfica de documentos
# ===========================================================================

SIZE_PORTADA_TITULO = 32
SIZE_H1 = 20
SIZE_H2 = 15
SIZE_H3 = 12
SIZE_BODY = 11
SIZE_CAPTION = 9
SIZE_FOOTER = 8


# ===========================================================================
# Metadata corporativa
# ===========================================================================

ORG_NAME = "SQA"
ORG_FULL_NAME = "SQA — Software Quality Assurance"
DOC_FOOTER_LEFT = "SQA · Gestión del Conocimiento"
"""Texto del pie de página izquierdo en documentos generados."""


# ===========================================================================
# Helpers
# ===========================================================================


def category_color(category_code: str) -> RgbColor:
    """Color del badge de una carpeta temática. Espejo de las
    `--color-cat-*` del frontend (globals.css). Default INK si el código
    no se reconoce (defensa contra tipos nuevos)."""
    mapping = {
        "PROC": RgbColor("1F8FE6"),  # 210 80% 50%
        "TEC": RgbColor("22C2C2"),  # 180 70% 45%
        "ARQ": RgbColor("8A33CC"),  # 270 60% 50%
        "HERR": RgbColor("EE8A17"),  # 30 85% 50%
        "NEG": RgbColor("D9337A"),  # 340 70% 50%
        "ENV": RgbColor("29A37A"),  # 160 60% 40%
        "EST": RgbColor("6B47D9"),  # 250 60% 55%
        "CONT": RgbColor("737373"),  # 0 0% 45%
    }
    return mapping.get(category_code, INK)


__all__ = [
    "AMARILLO",
    "AZUL_BRIGHT",
    "AZUL_CLARO",
    "AZUL_CORP",
    "AZUL_MEDIO",
    "AZUL_MEDIO_CLARO",
    "AZUL_OSCURO",
    "BLANCO",
    "COLOR_ACENTO",
    "COLOR_CUERPO",
    "COLOR_FONDO_BANDA",
    "COLOR_FONDO_TABLA_HEADER",
    "COLOR_SUBTITULO",
    "COLOR_TEXTO_SECUNDARIO",
    "COLOR_TITULO",
    "DOC_FOOTER_LEFT",
    "FONT_BODY",
    "FONT_DISPLAY",
    "FONT_FALLBACK_BODY",
    "FONT_FALLBACK_DISPLAY",
    "FONT_MONO",
    "GRIS_CLARO",
    "GRIS_TEXTO",
    "INK",
    "NARANJA",
    "NARANJA_SOFT",
    "ORG_FULL_NAME",
    "ORG_NAME",
    "RgbColor",
    "SIZE_BODY",
    "SIZE_CAPTION",
    "SIZE_FOOTER",
    "SIZE_H1",
    "SIZE_H2",
    "SIZE_H3",
    "SIZE_PORTADA_TITULO",
    "category_color",
]
