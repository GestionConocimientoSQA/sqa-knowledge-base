"""Services — casos de uso del negocio.

Cada función o clase aquí orquesta una operación significativa:
    - "crear sesión de captura"
    - "registrar mensaje del usuario y disparar streaming"
    - "aprobar item de ingesta"

Los services dependen de:
- `domain/` (entidades, errors)
- `ports/` (interfaces — NO adapters concretos)

Los services NO dependen de FastAPI, SQLAlchemy ni httpx directamente.
Reciben sus dependencias por inyección desde la capa `api/` o tests.
"""
