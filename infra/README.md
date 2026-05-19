# Infrastructure as Code · Azure (Bicep)

Plantillas Bicep que despliegan todo el stack productivo de SQA Knowledge Base
en Azure. **Diseñado para ser ejecutado por el equipo de TI** — el desarrollador
entrega las plantillas, TI las ejecuta.

> Estado actual: **esqueleto** (Fase 0). Los recursos se completan en Fase 11.

## Recursos desplegados

| Servicio Azure | Propósito | Sizing inicial |
|---|---|---|
| Azure Container Apps | Hosting de backend (FastAPI) y frontend (Next.js) | Consumption plan |
| Azure Database for PostgreSQL Flexible Server | DB transaccional + vectorial (pgvector) | Burstable B2s · 32GB |
| Azure Blob Storage | Documentos físicos (`base-conocimiento`, `inbox-pendientes`, `borradores`) | Standard LRS · hot+cool tiers |
| Azure Container Registry | Imágenes Docker | Basic |
| Azure Key Vault | Secrets (Anthropic key, conexiones) | Standard |
| Application Insights | Métricas, logs, traces | Free tier 5GB/mes |
| Microsoft Entra ID | SSO (incluido en M365) | — |
| Azure Monitor | Dashboards y alertas | Incluido |

Costo estimado: USD 71-106 / mes (sin contar Anthropic API).

## Estructura

```
infra/
├── README.md                  ← este archivo
├── main.bicep                 ← entrada principal (subscription scope)
├── modules/
│   ├── container-apps.bicep   ← ACR + ACA env + frontend + backend apps
│   ├── postgres.bicep         ← Flexible Server + pgvector extension
│   ├── storage.bicep          ← Storage account + 3 containers
│   ├── key-vault.bicep        ← Key Vault + access policies
│   ├── monitoring.bicep       ← Log Analytics + App Insights
│   └── networking.bicep       ← VNet + subnets + NSG
└── parameters/
    ├── dev.parameters.json
    ├── staging.parameters.json
    └── prod.parameters.json
```

## Despliegue (ejecutado por TI)

```bash
# Login
az login
az account set --subscription "<sub-id>"

# Validar
az deployment sub validate \
  --location eastus2 \
  --template-file infra/main.bicep \
  --parameters infra/parameters/dev.parameters.json

# What-if (preview de cambios)
az deployment sub what-if \
  --location eastus2 \
  --template-file infra/main.bicep \
  --parameters infra/parameters/dev.parameters.json

# Deploy
az deployment sub create \
  --location eastus2 \
  --template-file infra/main.bicep \
  --parameters infra/parameters/dev.parameters.json
```

## Naming convention

```
<resource-type>-sqa-kb-<env>[-<region-short>]
```

Ejemplos:
- `rg-sqa-kb-dev` (resource group)
- `acr-sqa-kb-dev`
- `kv-sqa-kb-dev`
- `postgres-sqa-kb-dev`
- `aca-sqa-kb-frontend-dev`
- `aca-sqa-kb-backend-dev`

## Entornos

| Env | Subscription | Region | Sizing |
|---|---|---|---|
| dev | SQA-Dev | East US 2 | Burstable + Consumption |
| staging | SQA-Prod | East US 2 | Como prod pero 1 réplica |
| prod | SQA-Prod | East US 2 | DB GeneralPurpose + 2 réplicas |
