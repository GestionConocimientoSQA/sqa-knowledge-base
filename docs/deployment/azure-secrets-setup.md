# Setup de secrets de GitHub Actions ↔ Azure

> **Audiencia:** TI · **Bloquea:** workflow `build-and-push.yml` (Fase 11) y
> deploy real del backend/frontend a Azure Container Apps.
> **Estado:** ⬜ Pendiente — esperando que TI cree el App Registration
> en Entra ID.

## Contexto

El workflow `.github/workflows/build-and-push.yml` construye las imágenes
Docker de `frontend` y `backend` y las sube a **Azure Container Registry**
usando autenticación **OIDC** (federated credentials) — sin password ni
client secret. Para que esto funcione hace falta:

1. Un **App Registration** en Entra ID con permisos de push al ACR.
2. **Federated credentials** que confíen en GitHub Actions sobre este repo.
3. **3 secrets + 1 variable** configurados en el repo GitHub.

Mientras no esté configurado el workflow corre pero su job `preflight`
detecta el vacío y skipea el push (no falla, solo emite warning).

## Variables y secrets requeridos

| Nombre | Tipo | Valor esperado | Cómo obtenerlo |
|---|---|---|---|
| `AZURE_ACR_NAME` | **Variable** (no secret) | Nombre del ACR sin sufijo (`sqakbacr`) | TI lo decide al crear el ACR; va en `infra/parameters/<env>.parameters.json` |
| `AZURE_CLIENT_ID` | **Secret** | UUID del App Registration | Portal Entra ID → App registrations → tu app → Overview → "Application (client) ID" |
| `AZURE_TENANT_ID` | **Secret** | UUID del tenant SQA | Portal Entra ID → Overview → "Tenant ID" |
| `AZURE_SUBSCRIPTION_ID` | **Secret** | UUID de la suscripción donde vive el ACR | Portal Azure → Subscriptions → la del proyecto SQA |

## Pasos para TI

### 1. Crear App Registration

```bash
# Logueado como admin del tenant SQA con permisos de App Registration:
az ad app create \
  --display-name "sqa-knowledge-base-ci" \
  --sign-in-audience AzureADMyOrg

# Obtener el client-id devuelto:
APP_ID=$(az ad app list --display-name "sqa-knowledge-base-ci" --query '[0].appId' -o tsv)

# Crear service principal asociado:
az ad sp create --id $APP_ID
```

### 2. Asignar rol `AcrPush` sobre el ACR

```bash
# Asumiendo que el ACR ya existe (lo crea Bicep en Fase 11):
ACR_RESOURCE_ID="/subscriptions/<SUBSCRIPTION_ID>/resourceGroups/<RG>/providers/Microsoft.ContainerRegistry/registries/<ACR_NAME>"

az role assignment create \
  --assignee $APP_ID \
  --role "AcrPush" \
  --scope $ACR_RESOURCE_ID
```

### 3. Configurar federated credential para GitHub Actions

Esto es el punto crítico del OIDC: Azure confía en GitHub para emitir
tokens en nombre de este repo.

```bash
cat > federated-credential.json <<EOF
{
  "name": "github-actions-master",
  "issuer": "https://token.actions.githubusercontent.com",
  "subject": "repo:GestionConocimientoSQA/sqa-knowledge-base:ref:refs/heads/master",
  "audiences": ["api://AzureADTokenExchange"]
}
EOF

az ad app federated-credential create \
  --id $APP_ID \
  --parameters federated-credential.json
```

> **Importante:** el campo `subject` es exacto. Si más adelante se
> agregan branches que también deben pushear (ej. `release/*`), se
> agrega otra federated credential con su propio `subject` pattern
> (`repo:.../...:ref:refs/heads/release/*`).

### 4. Agregar los secrets/vars en GitHub

```bash
# Desde tu máquina, con gh CLI logueado en GestionConocimientoSQA:
gh variable set AZURE_ACR_NAME --body "sqakbacr" \
  --repo GestionConocimientoSQA/sqa-knowledge-base

gh secret set AZURE_CLIENT_ID --body "$APP_ID" \
  --repo GestionConocimientoSQA/sqa-knowledge-base

gh secret set AZURE_TENANT_ID --body "<TENANT_ID>" \
  --repo GestionConocimientoSQA/sqa-knowledge-base

gh secret set AZURE_SUBSCRIPTION_ID --body "<SUBSCRIPTION_ID>" \
  --repo GestionConocimientoSQA/sqa-knowledge-base
```

(O via UI: Settings → Secrets and variables → Actions.)

### 5. Verificar

Disparar manualmente el workflow:

```bash
gh workflow run build-and-push.yml --ref master \
  --repo GestionConocimientoSQA/sqa-knowledge-base \
  -f app=both
```

El job `login` debería pasar (token OIDC intercambiado por Azure access
token) y los jobs `build_frontend` / `build_backend` deberían subir
las imágenes a `<ACR_NAME>.azurecr.io/sqa-kb/{frontend,backend}`.

## Notas operativas

- **El secret de App Registration NO se guarda** — todo el flow es
  OIDC. Si alguien filtra el `client-id` no puede usarlo sin la
  federated credential configurada. Si la federated credential se
  rota, basta con borrarla del App Registration.
- **El permiso `AcrPush` es de menor privilegio que `Owner`** — solo
  permite push de imágenes, no editar el ACR ni borrar repos.
- **Cuando se agregue staging/prod**, cada entorno tendrá su propia
  federated credential con `subject` específico (ej. con environment
  protection rules en GitHub).
- **Si el repo cambia de visibilidad o se transfiere de owner**, hay
  que recrear las federated credentials con el nuevo `subject`.

## Referencia upstream

- [GitHub OIDC con Azure (Microsoft Learn)](https://learn.microsoft.com/azure/developer/github/connect-from-azure-openid-connect)
- [azure/login@v2 action](https://github.com/Azure/login)

## Estado actual del repo

| Item | Estado |
|---|---|
| Workflow `build-and-push.yml` | ✅ Listo (con `preflight` que detecta secrets faltantes) |
| Federated credential en Entra | ⬜ Pendiente TI |
| Rol `AcrPush` asignado | ⬜ Pendiente TI |
| Variable `AZURE_ACR_NAME` en GitHub | ⬜ Pendiente |
| Secrets `AZURE_*` en GitHub | ⬜ Pendiente |
| Primer push exitoso a ACR | ⬜ Pendiente (validación final) |
