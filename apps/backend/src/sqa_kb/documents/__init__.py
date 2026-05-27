"""Generación y extracción de documentos (Fase 4).

Submódulos:
- `branding`: paleta + tipografía SQA, helpers de estilo reusables.
- `generators/`: DOCX, PPTX, XLSX, PDF, Markdown.
- `extractors/`: lectura de DOCX, PPTX, PDF, XLSX → texto + estructura.
- `anonymizer`: filtro PII regex (interfaz lista para Presidio).
- `filename`: builder de nombres `[TIPO]-[tema]-[YYYY-MM-DD].ext`.

Regla de imports: este paquete NO depende de `api/` ni de `agent/`.
Los generadores reciben datos de dominio y devuelven `bytes`; el caller
(agente o endpoint) decide qué hacer con ellos (subir a Blob, devolver
en la response, etc.).
"""
