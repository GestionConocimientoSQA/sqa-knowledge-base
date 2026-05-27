"""Etiquetas legibles de los 11 tipos de documento (Playbook SQA v1.3).

Espejo de `DOC_TYPES` en
`adapters/repositories/postgres/seed.py` y de los `DocTypeCode` del
dominio. Se usa para mostrar el nombre completo del tipo en la portada
de los documentos generados (p. ej. "POL" → "Política").

Nota sobre estructura por tipo
==============================
El ROADMAP (§7.3) lista los 11 códigos pero la estructura de secciones
de cada tipo vive en el "Playbook SQA v1.3", un documento externo no
incluido en el repo. Por eso los generadores de Fase 4 producen una
**estructura común** (metadata + tema + contenido + precisiones), que
es la misma que ya genera el agente desde Fase 2. Cuando el playbook
esté disponible, se puede extender `DOC_TYPE_SECTIONS` por tipo sin
tocar los generadores.
"""

from __future__ import annotations

DOC_TYPE_LABELS: dict[str, str] = {
    "POL": "Política",
    "PROC": "Procedimiento",
    "GUIA": "Guía",
    "INST": "Instructivo",
    "SERV": "Servicio",
    "MTEC": "Memoria técnica",
    "ACEL": "Acelerador",
    "UEN": "UEN",
    "ARCL": "Arquetipo cliente",
    "FORM": "Formato",
    "PRES": "Presentación",
}

CATEGORY_LABELS: dict[str, str] = {
    "PROC": "Procesos de Pruebas",
    "TEC": "Conocimiento Técnico",
    "ARQ": "Arquitectura y Decisiones Técnicas",
    "HERR": "Herramientas y Accesos",
    "NEG": "Reglas de Negocio del Cliente",
    "ENV": "Ambientes y Datos de Prueba",
    "EST": "Estrategia y Metodología de Pruebas",
    "CONT": "Contactos y Estructura del Cliente",
}


def doc_type_label(code: str) -> str:
    """Nombre legible del tipo. Cae al código crudo si no se reconoce."""
    return DOC_TYPE_LABELS.get(code, code)


def category_label(code: str) -> str:
    """Nombre legible de la carpeta. Cae al código crudo si no se reconoce."""
    return CATEGORY_LABELS.get(code, code)
