# Manejo de secretos en desarrollo

## Principio

**Ningún secreto vive en el repo.** Ni `.env`, ni `.env.local`, ni archivos
similares se commitean. La regla es absoluta — aun rotada, una API key
expuesta en git history es una API key comprometida.

## Estructura

```
C:\AriaAppGK\
├── credentials.env         ← acá viven los secretos (FUERA del repo)
└── sqa-knowledge-base\     ← el repo
    ├── .env                ← variables NO sensibles, gitignored igualmente
    ├── .env.example        ← plantilla pública (este sí va a git)
    └── apps\
        ├── backend\.env    ← override específico de backend (gitignored)
        └── frontend\.env.local
```

## Cómo se cargan

### Backend (FastAPI + Pydantic Settings)

```python
# apps/backend/src/sqa_kb/config.py
class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=[
            "../../.env",                  # variables compartidas del monorepo
            "../../../credentials.env",    # secretos locales (gana por orden)
            ".env",                        # override por servicio
        ],
        env_file_encoding="utf-8",
    )
```

El orden importa: el último archivo en la lista pisa a los anteriores.

### Frontend (Next.js)

Next.js carga automáticamente `.env.local` y `.env`. Para inyectar secretos del
`credentials.env` raíz al frontend, NO se hace — el frontend solo recibe
variables `NEXT_PUBLIC_*` que son por definición públicas. Cualquier secreto
real se llama desde el backend.

### Docker Compose

```yaml
# docker-compose.yml
services:
  backend:
    env_file:
      - .env
      - ../credentials.env   # opcional, solo si existe
```

Si `../credentials.env` no existe, compose tira un warning pero no falla.

## Producción (Azure)

En producción los secretos viven en **Azure Key Vault**. La aplicación los
referencia por nombre vía Managed Identity. Ver `docs/deployment/secrets-mapping.md`
(pendiente, Fase 11) para el mapeo completo `nombre-en-.env` → `nombre-en-KeyVault`.

## Checklist antes de hacer commit

- [ ] `git status` no muestra ningún `.env`, `credentials.env`, `*.pem`, `*.key`.
- [ ] `git diff --staged | grep -iE "api[_-]?key|secret|password|token"` no muestra valores reales.
- [ ] Si agregaste una nueva variable, está documentada en `.env.example`.
