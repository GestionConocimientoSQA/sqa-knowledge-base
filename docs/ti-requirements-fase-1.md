# Solicitud a TI — Pre-requisitos Fase 1 (Backend + Auth Entra ID)

> **Solicitante:** Andrés Altamiranda · GK Lead SQA
> **Proyecto:** SQA Knowledge Base
> **Fecha:** 2026-05-20
> **Bloquea:** Fases 1, 2, 3, 4 del backend; Fase 11 (deploy a Azure)

## Contexto

El proyecto SQA Knowledge Base es una app web standalone que reemplaza al agente actual de captura/consulta/ingesta del conocimiento del equipo SQA. El frontend ya está construido al 100% del scope planificado (Fases 5-7 ✅) operando contra mocks-stub. Para arrancar Fase 1 (backend con persistencia PostgreSQL + autenticación con Microsoft Entra ID) necesitamos que TI provisione los recursos abajo en el tenant SQA.

El stack está definido en el `ROADMAP-IMPLEMENTACION-SQA-KB.md` y se despliega en Azure (Container Apps + PostgreSQL Flexible Server + Blob + Key Vault + App Insights). Las plantillas Bicep están en `infra/` listas para que TI revise.

---

## 1. Crítico para arrancar Fase 1

Sin estos items el código backend no puede validarse end-to-end (login real, JWT validation, `current_user` dependency).

### 1.1 App Registration en Microsoft Entra ID (tenant SQA)

Crear un App Registration con la configuración siguiente:

| Campo | Valor |
|---|---|
| Display name | `SQA Knowledge Base` (o el que prefieran) |
| Supported account types | **Single tenant** (solo cuentas del tenant SQA) |
| Platform type | **Single-page application (SPA)** |
| Redirect URIs (dev) | `http://localhost:3000` |
| Redirect URIs (staging) | _(URL que TI defina cuando esté el ambiente)_ |
| Redirect URIs (prod) | _(URL que TI defina cuando esté el ambiente)_ |
| Logout URL | `http://localhost:3000/login` (y los equivalentes de staging/prod) |
| Implicit grant | **Desactivado** (usamos PKCE, no implicit flow) |

**Datos que necesitamos de vuelta:**
- `Application (client) ID` — UUID
- `Directory (tenant) ID` — UUID

### 1.2 API permissions

Sobre el App Registration recién creado, agregar (todas **delegated**):

- **Microsoft Graph** → `User.Read` (leer perfil del usuario logueado)
- **Microsoft Graph** → `openid`, `profile`, `email` (claims básicos del ID token)

**Admin consent** requerido para `User.Read` (TI lo otorga desde el tenant).

### 1.3 Expose an API (para validación de tokens en backend)

En el mismo App Registration, sección **Expose an API**:

| Campo | Valor sugerido |
|---|---|
| Application ID URI | `api://sqa-kb` o `api://<client-id>` |
| Scope name | `access_as_user` |
| Who can consent | Admins and users |
| Admin consent display name | `Usar SQA Knowledge Base` |
| Admin consent description | `Permite a la app autenticar al usuario para acceder a su Knowledge Base.` |
| State | Enabled |

**Authorized client applications**: agregar el `client-id` del propio App Registration (auto-autorización SPA → API).

### 1.4 Token configuration (opcional pero recomendado)

Agregar **Optional claims** al ID token:

- `email`
- `family_name`
- `given_name`
- `upn`

Esto nos evita un round-trip a Microsoft Graph para obtener nombre/apellido en el primer login.

---

## 2. Necesario para Fase 11 (deploy a Azure)

Estos items no bloquean el desarrollo de Fase 1 pero sí el deploy real. Idealmente arrancarlos en paralelo.

### 2.1 Azure subscriptions

Definir y compartir los IDs:

| Ambiente | Subscription ID |
|---|---|
| dev | _________________ |
| staging | _________________ |
| prod | _________________ |

Si los 3 ambientes viven en la misma subscription, indicarlo y separamos por Resource Group.

### 2.2 Resource Groups

Crear (o confirmar naming convention SQA):

- `rg-sqa-kb-dev`
- `rg-sqa-kb-staging`
- `rg-sqa-kb-prod`

### 2.3 Azure Container Registry

Confirmar si usamos un ACR existente del tenant SQA o creamos uno nuevo. Necesitamos:

- Nombre del ACR (`AZURE_ACR_NAME`)
- Que TI nos dé permiso `AcrPush` desde el Service Principal (ver 2.4)

### 2.4 Service Principal con Federated Identity Credentials (OIDC) para GitHub Actions

Crear un SP que GitHub Actions usa para pushear imágenes al ACR y desplegar Bicep **sin secrets en GitHub** (federación OIDC).

**Federated credentials a crear** (subject identifier):

```
repo:<github-org>/<github-repo>:ref:refs/heads/main
repo:<github-org>/<github-repo>:environment:dev
repo:<github-org>/<github-repo>:environment:staging
repo:<github-org>/<github-repo>:environment:prod
```

**Audience**: `api://AzureADTokenExchange`

**Role assignments del SP**:

| Scope | Role |
|---|---|
| ACR | `AcrPush` |
| `rg-sqa-kb-dev` | `Contributor` |
| `rg-sqa-kb-staging` | `Contributor` |
| `rg-sqa-kb-prod` | `Contributor` (o más restringido si lo prefieren) |

**Datos que necesitamos de vuelta:**
- `AZURE_CLIENT_ID` del SP (UUID)

---

## 3. Conditional Access y políticas (información necesaria)

Necesitamos saber si el tenant SQA tiene políticas de Conditional Access que afecten a la app, para que el flujo MSAL del frontend las contemple:

- [ ] ¿MFA obligatorio? (en qué condiciones)
- [ ] ¿Restricciones por IP / país?
- [ ] ¿Device compliance / Intune requerido?
- [ ] ¿Token lifetime customizado? (defaults: ID token 1 hora, refresh token 90 días)
- [ ] ¿Conditional Access App Filter aplicable a la app nueva?

---

## 4. Opcional / Futuro (no bloquea Fase 1)

Estos items los necesitaremos más adelante; los listamos para que TI los considere en su roadmap.

### 4.1 Microsoft Graph · Mail.Send (Fase 2 — notificaciones)

Para enviar alertas a Owners de carpeta cuando aparezca contenido relevante o haya gaps detectados.

- Permission: `Mail.Send` (**application**, no delegated)
- Admin consent requerido
- Buzón de origen sugerido: `noreply-sqa-kb@sqa.co` (o el que TI prefiera)

### 4.2 Groups claim (RBAC por grupo de AD)

Si TI ya tiene grupos de AD definidos para roles internos (ej: `SQA-QA-Leads`, `SQA-GK-Lead`), podemos mapearlos al claim `groups` del token y derivar permisos sin mantener una tabla `users` manual. Decisión queda abierta — por defecto vamos con tabla propia y mapping en backend.

### 4.3 Application Insights workspace

Existe un workspace centralizado del tenant que podamos usar, o creamos uno nuevo en `rg-sqa-kb-{env}`.

---

## 5. Resumen — qué necesitamos del bandejazo de TI

| # | Item | Bloquea Fase | Tiempo estimado TI |
|---|---|---|---|
| 1.1 | App Registration en Entra ID | F1 (auth) | 30 min |
| 1.2 | API permissions + admin consent | F1 (auth) | 15 min |
| 1.3 | Expose an API + scope custom | F1 (auth backend) | 15 min |
| 1.4 | Optional claims (opcional) | — | 5 min |
| 2.1 | Subscription IDs por ambiente | F11 (deploy) | 15 min |
| 2.2 | Resource Groups | F11 (deploy) | 15 min |
| 2.3 | Azure Container Registry | F11 (build/push) | 30 min |
| 2.4 | Service Principal con OIDC | F11 (CI/CD) | 1 hr |
| 3   | Info de Conditional Access | F1 (MSAL flow) | 15 min |

**Total estimado:** ~3 hr de trabajo distribuido.

---

## 6. Qué entregamos nosotros una vez que TI confirme

Una vez recibidos los IDs y confirmaciones de la sección 1 y 2, nosotros:

1. Configuramos las variables de entorno locales (`credentials.env` ya gitignored).
2. Configuramos los **GitHub Secrets**: `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID`.
3. Configuramos las **GitHub Variables**: `AZURE_ACR_NAME`.
4. Activamos el workflow `build-and-push.yml` (ya está pero condicionado a las vars).
5. Implementamos el JWT validator en backend (`src/sqa_kb/auth/`) con JWKS cache.
6. Reemplazamos el auth-stub del frontend por `@azure/msal-react` real (Fase 11).

---

## Anexos

- `infra/README.md` — contrato con TI + naming convention de los recursos Bicep
- `infra/main.bicep` — orquesta los 6 módulos (networking, monitoring, KV, storage, postgres, container-apps)
- `infra/parameters/{dev,staging,prod}.parameters.json` — parámetros por ambiente
- `ROADMAP-IMPLEMENTACION-SQA-KB.md` — plan completo de 12 fases (en raíz del proyecto, un nivel arriba)

Cualquier duda sobre el stack técnico, decisiones de arquitectura o el plan de fases queda a disposición.

— Andrés Altamiranda · andres.altamiranda@sqasa.co
