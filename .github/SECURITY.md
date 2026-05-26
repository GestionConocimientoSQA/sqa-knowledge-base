# Política de seguridad

> **SQA Knowledge Base** — política de divulgación responsable de vulnerabilidades.

## Versiones soportadas

Este proyecto está en desarrollo activo. Solo la rama `master` recibe
parches de seguridad. No mantenemos branches LTS — el avance se da por
fases del [ROADMAP](../ROADMAP-IMPLEMENTACION-SQA-KB.md).

| Branch | Soportada |
|---|---|
| `master` | ✅ |
| Branches de fase (`fase-*`) | ❌ (mergean a master y se cierran) |
| Tags / releases | _no aplicable hasta paso a producción (Fase 11)_ |

## Reportar una vulnerabilidad

**Por favor NO abras un issue público de GitHub para reportar
vulnerabilidades.** Los issues públicos quedan indexados antes de que
podamos parchear y eso pone en riesgo a otros usuarios del código.

En su lugar, usá uno de estos canales:

### Opción A — GitHub Security Advisories (preferida)

Andá a la pestaña [**Security**](../../security/advisories/new) del repo
y abrí un advisory privado. Solo el equipo del repo y vos lo ven hasta
que se cierre el caso.

### Opción B — Email directo

Mandá un correo a **andres.altamiranda@sqasa.co** con:

- **Subject:** `[SECURITY] sqa-knowledge-base — <resumen corto>`
- **Body** sugerido:
  - Descripción del problema.
  - Pasos para reproducirlo (idealmente PoC mínimo).
  - Impacto estimado (qué se puede comprometer).
  - Versión / commit SHA afectado.
  - Si corresponde, una propuesta de mitigación.

Si querés cifrar el reporte podés pedirme una clave pública por el
mismo canal.

## Qué esperar después del reporte

| Tiempo | Acción |
|---|---|
| **48 horas** | Acuse de recibo + assignment a alguien que lo trabaje. |
| **7 días** | Triage inicial: confirmación de la vulnerabilidad y severidad estimada (CVSS). |
| **30 días** | Patch listo en `master` (puede ser más rápido si la severidad es Critical/High). |
| **Posterior al fix** | Advisory público en GitHub con créditos al reportante (si así lo prefiere). |

Si en algún punto pensás que la respuesta se está demorando o el
problema no se está tomando con la seriedad necesaria, mandame un
follow-up por el mismo canal.

## Alcance de esta política

Esta política cubre **solo el código de este repositorio**:

- `apps/frontend/` (Next.js + cliente del KB).
- `apps/backend/` (FastAPI + agente Aria + RAG).
- `infra/` (Bicep IaC para Azure).
- Workflows en `.github/workflows/`.
- Documentación en `docs/`.

**Fuera de scope:**

- Vulnerabilidades de las **dependencias upstream** (Anthropic SDK,
  Cohere, FastAPI, Next.js, etc.) — reportarlas directamente al
  maintainer de cada paquete. Si la vulnerabilidad afecta a este
  proyecto por el uso que le damos, sí entra en scope.
- **Infraestructura Azure desplegada** por SQA — eso lo gestiona el
  equipo de TI de SQA bajo sus propios procesos de seguridad.
- **Datos productivos** en el KB de SQA (si los hubiera) — son
  responsabilidad de TI SQA / Gestión del Conocimiento.

## Reportes que NO son security

Si encontrás un bug funcional que **no es una vulnerabilidad**, o
querés sugerir una feature, abrí un issue público normal en la
pestaña [Issues](../../issues). Ahí están las plantillas de bug
report y feature request.

Ejemplos típicos de **no security**:

- "El botón X no se ve bien en mobile."
- "Los tests E2E fallan intermitentemente."
- "La docs de la API tiene un error de tipeo."

Ejemplos típicos de **sí security**:

- Inyección SQL / NoSQL / template injection.
- XSS persistente o reflejado.
- Bypass de auth o de IDOR (en endpoints `/sessions/{id}/*`).
- Path traversal en `/ingestion` (uploads).
- Filtración de secrets vía logs o errores en respuestas.
- Token / cookie con configuración insegura.
- Dependencia con CVE crítica que no fue parcheada.

## Reconocimientos

A los reportantes que sigan esta política les vamos a:

- Acreditarlos en el advisory público (a menos que prefieran anonimato).
- Mencionarlos en `docs/security/credits.md` (a crearse en Fase 10).

Gracias por ayudar a mantener seguro este proyecto.

---

_Última actualización: 2026-05-26 · Andrés Altamiranda · GK Lead SQA_
