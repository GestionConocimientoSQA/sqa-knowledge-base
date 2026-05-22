"""Domain layer — entidades, value objects, errors. Sin dependencias externas.

Es el corazón del negocio. Define el lenguaje del dominio SQA Knowledge Base:
qué es un usuario, una sesión, un documento, qué reglas los rigen.

Regla de imports (Clean Architecture):
    domain  ← nadie (sin imports de otras capas del proyecto)
    services → domain
    adapters → ports → domain
    api → services → domain

Si una clase del domain importa algo de FastAPI, SQLAlchemy o un HTTP client
externo, está mal: hay que mover la dependencia a `adapters/` o `ports/`.
"""
