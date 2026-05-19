# Convenciones de código

## Generales

- **Idioma:** comentarios y docs en español; código y nombres técnicos en inglés.
- **Sin emojis** en código, UI ni commits (salvo casos puntuales acordados).
- **Sin `any`/`unknown`** sin justificación en TS. Tipos del dominio en
  `src/types/domain.ts`.
- **Sin variables globales** salvo configuración inmutable.

## SOLID (regla del repo)

| Principio | Aplicación |
|---|---|
| SRP | Cada archivo/módulo tiene una responsabilidad. UI ≠ data fetching ≠ business logic. |
| OCP | Extender via props/composición/strategy, no modificar shadcn/ui base. |
| LSP | Tipos del dominio estables; adapters intercambiables (auth stub ↔ MSAL). |
| ISP | Hooks granulares (`useAuth`, `useRequireAuth`) — evitar mega-contexts. |
| DIP | UI depende de `lib/api/*`, no de mocks ni HTTP directo. |

## TypeScript

- `strict: true` + `noUncheckedIndexedAccess: true`.
- Server Components por defecto; Client Components solo cuando necesario.
- Componentes funcionales con hooks (sin clases).
- Hooks personalizados con prefijo `use-`.
- Estados explícitos en listados: **loading / error / empty / populated**.

## Python

- 3.12+, type hints obligatorios en signatures públicas.
- Async/await por defecto (no mezclar sync y async en endpoints).
- `ruff` para lint + formato (configurado en `pyproject.toml`).
- `mypy --strict` en `domain/` y `agent/`; modo gradual en el resto.
- Docstrings estilo Google en clases/funciones públicas.
- Inyección de dependencias via FastAPI `Depends`.
- Logs estructurados con `structlog` (key=value, no string interpolation).

## Naming

- **URLs:** kebab-case (`/document-types`).
- **Payloads JSON:** snake_case (`document_type_code`).
- **TS identifiers:** camelCase locales, PascalCase componentes y tipos.
- **Python identifiers:** snake_case funciones/variables, PascalCase clases.
- **Branches git:** `feat/...`, `fix/...`, `refactor/...`, `docs/...`, `chore/...`.

## Git

- **Conventional Commits** (`feat:`, `fix:`, `refactor:`, etc.).
- **Squash merge** a `main`.
- `main` protegido — PR obligatorio.
- PR template con checklist (Fase 1+).

## Tests

- Targets de cobertura por capa: ver `docs/development/testing.md`.
- Tests primero en lógica pura (`lib/`), después en componentes.

## Imports (frontend)

```ts
// Orden:
// 1. externos (react, next, third-party)
// 2. componentes ui (@/components/ui)
// 3. componentes propios (@/components, @/lib, @/hooks)
// 4. tipos (@/types)
// 5. estilos
```

## Pull Requests

- Título: imperativo, < 70 chars (`feat: add chat streaming SSE consumer`)
- Body: contexto + qué + cómo + checklist de testing.
- Vincular a issues si existen.
