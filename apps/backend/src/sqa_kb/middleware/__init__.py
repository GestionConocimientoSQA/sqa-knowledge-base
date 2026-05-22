"""HTTP middleware del backend.

Cada módulo expone un middleware ASGI montable en `main.py`:
- `request_id` — genera o propaga `X-Request-ID` y lo expone en logs
- `error_handler` — convierte errores de dominio a respuestas HTTP

Diseñados para ser stateless y testeables con TestClient.
"""
