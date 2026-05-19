# Documentación · SQA Knowledge Base

```
docs/
├── architecture/      Decisiones de diseño y arquitectura
│   ├── overview.md
│   ├── data-model.md            (Fase 1)
│   ├── agent-state-machine.md   (Fase 2)
│   ├── security.md              (Fase 10)
│   └── adr/                     Architecture Decision Records
├── deployment/        Operación en Azure (entregable a TI)
│   ├── DEPLOYMENT.md            (Fase 11)
│   ├── RUNBOOK.md               (Fase 11)
│   ├── secrets-mapping.md       (Fase 11)
│   ├── monitoring-dashboard.md  (Fase 11)
│   └── rollback-procedures.md   (Fase 11)
├── development/       Cómo trabajar en el repo
│   ├── getting-started.md
│   ├── conventions.md
│   ├── secrets-handling.md
│   ├── testing.md
│   ├── adding-a-document-type.md
│   └── adding-a-skill.md
└── api/
    └── openapi.yaml             (autogenerado por FastAPI)
```

Cada doc tiene su público:

- **architecture/** — para futuros devs y arquitectos que necesitan entender *por qué* algo se diseñó así.
- **deployment/** — para el equipo de TI de SQA que opera la app día a día.
- **development/** — para Andrés (o quien lo reemplace) trabajando código.
