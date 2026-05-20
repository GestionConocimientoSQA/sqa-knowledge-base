import type {
  Role,
  RoleId,
  Category,
  DocType,
  DocumentItem,
  HotTopic,
  IncomingCitation,
  IngestionItem,
  RecentActivityItem,
  Stage,
} from "@/types/domain";

export const ROLES: Record<RoleId, Role & { name: string; email: string }> = {
  capturador: {
    id: "capturador",
    label: "Capturador (Colaborador)",
    sub: "QA, Automation Engineer, Test Lead, áreas transversales",
    name: "Lucía Vargas",
    email: "lucia.vargas@sqa.co",
    icon: "user-pen",
  },
  owner: {
    id: "owner",
    label: "Owner de carpeta",
    sub: "Responsable formal de una carpeta temática",
    name: "Camila Pereyra",
    email: "camila.pereyra@sqa.co",
    icon: "users-round",
  },
  gklead: {
    id: "gklead",
    label: "GK Lead",
    sub: "Líder de Gestión del Conocimiento",
    name: "Andrés Altamiranda",
    email: "andres.altamiranda@sqa.co",
    icon: "compass",
  },
};

/**
 * OIDs estables de autores mock. Mapean al `oid` que devolverá Entra ID en
 * Fase 1 — en stub son strings hardcoded, en backend serán los Object IDs
 * reales del JWT. La consistencia entre `autorOid` del documento y `oid` del
 * `AuthUser` permite que `listMyCaptures` filtre correctamente.
 */
export const AUTHOR_OIDS = {
  lucia: "oid-capturador-lucia",
  camila: "oid-owner-camila",
  andres: "oid-gklead-andres",
  diego: "oid-perf-diego",
  mateo: "oid-aut-mateo",
  sofia: "oid-qa-sofia",
  tomas: "oid-arch-tomas",
  renata: "oid-test-renata",
} as const;

export const FOLDERS: Category[] = [
  { code: "PROC", label: "Procesos", docs: 84, vigentes: 76, autoritativos: 41, scoreAvg: 3.8, obsolescencia: 4 },
  { code: "TEC", label: "Técnico", docs: 142, vigentes: 128, autoritativos: 88, scoreAvg: 4.1, obsolescencia: 6 },
  { code: "ARQ", label: "Arquitectura", docs: 47, vigentes: 44, autoritativos: 38, scoreAvg: 4.4, obsolescencia: 1 },
  { code: "HERR", label: "Herramientas", docs: 96, vigentes: 81, autoritativos: 52, scoreAvg: 3.6, obsolescencia: 9 },
  { code: "NEG", label: "Negocio", docs: 38, vigentes: 35, autoritativos: 28, scoreAvg: 3.9, obsolescencia: 2 },
  { code: "ENV", label: "Ambientes", docs: 29, vigentes: 24, autoritativos: 17, scoreAvg: 3.5, obsolescencia: 3 },
  { code: "EST", label: "Estándares", docs: 22, vigentes: 22, autoritativos: 22, scoreAvg: 4.6, obsolescencia: 0 },
  { code: "CONT", label: "Contexto", docs: 18, vigentes: 15, autoritativos: 9, scoreAvg: 3.4, obsolescencia: 2 },
];

export const DOC_TYPES: DocType[] = [
  { code: "POL", label: "Política" },
  { code: "PROC", label: "Procedimiento" },
  { code: "GUIA", label: "Guía" },
  { code: "INST", label: "Instructivo" },
  { code: "SERV", label: "Servicio" },
  { code: "MTEC", label: "Memoria técnica" },
  { code: "ACEL", label: "Acelerador" },
  { code: "UEN", label: "UEN" },
  { code: "ARCL", label: "Arquetipo cliente" },
  { code: "FORM", label: "Formato" },
  { code: "PRES", label: "Presentación" },
];

export const ETAPAS: Stage[] = [
  { id: 0, label: "Bienvenida", short: "0", icon: "hand" },
  { id: 1, label: "Identificación", short: "1", icon: "user-search" },
  { id: 2, label: "Captura libre", short: "2", icon: "mic" },
  { id: 3, label: "Profundización", short: "3", icon: "telescope" },
  { id: 4, label: "Validación", short: "4", icon: "check-check" },
  { id: 5, label: "Generación", short: "5", icon: "file-output" },
];

/**
 * Mocks de documentos del catálogo. Distribuidos para que filtros, sort y
 * paginación tengan resultados representativos. Los counts de FOLDERS son
 * agregados de producción "ficticia" — el mock contiene una muestra menor
 * pero suficiente para validar UX.
 *
 * Nuevas piezas se agregan al final con `id` único en formato
 * `[CARPETA]-[slug]-[YYYY-MM-DD]` (mismo que produce el agente real).
 */
export const DOCS: DocumentItem[] = [
  // TEC (10) — carpeta con más docs en producción
  {
    id: "TEC-flakiness-detection-2026-04-22",
    titulo: "Detección y aislamiento de tests flaky en suite de regresión",
    carpeta: "TEC", tipo: "MTEC", autoritativo: true, estado: "vigente",
    autor: "Lucía Vargas", autorOid: AUTHOR_OIDS.lucia, rol: "Automation Engineer",
    fecha: "2026-04-22", revision: "2026-04-22", version: "1.2",
    citas: 47, score: 4.4, anonimizado: true, fragmentos: 38, paginas: 14, formato: "DOCX",
    aprobador: "Mateo Robles", fechaAprobacion: "2026-04-25",
    tags: ["regresión", "flakiness", "CI/CD", "Playwright"],
  },
  {
    id: "TEC-data-driven-cypress-2026-03-05",
    titulo: "Estrategia data-driven en Cypress con fixtures versionadas",
    carpeta: "TEC", tipo: "GUIA", autoritativo: true, estado: "vigente",
    autor: "Mateo Robles", autorOid: AUTHOR_OIDS.mateo, rol: "Automation Lead",
    fecha: "2026-03-05", revision: "2026-04-12", version: "1.1",
    citas: 28, score: 4.2, anonimizado: false, fragmentos: 26, paginas: 11, formato: "DOCX",
    aprobador: "Andrés Altamiranda", fechaAprobacion: "2026-03-08",
    tags: ["Cypress", "fixtures", "data-driven"],
  },
  {
    id: "TEC-api-contract-testing-2026-02-28",
    titulo: "Contract testing con Pact entre microservicios de pagos",
    carpeta: "TEC", tipo: "MTEC", autoritativo: true, estado: "vigente",
    autor: "Tomás Iglesias", autorOid: AUTHOR_OIDS.tomas, rol: "QA Architect",
    fecha: "2026-02-28", revision: "2026-02-28", version: "1.0",
    citas: 35, score: 4.5, anonimizado: true, fragmentos: 42, paginas: 18, formato: "DOCX",
    aprobador: "Andrés Altamiranda", fechaAprobacion: "2026-03-02",
    tags: ["Pact", "contract-testing", "microservicios", "pagos"],
  },
  {
    id: "TEC-e2e-mobile-android-2026-01-19",
    titulo: "E2E mobile Android con Detox sobre app híbrida",
    carpeta: "TEC", tipo: "INST", autoritativo: false, estado: "vigente",
    autor: "Sofía Núñez", autorOid: AUTHOR_OIDS.sofia, rol: "Mobile QA",
    fecha: "2026-01-19", revision: "2026-03-22", version: "1.3",
    citas: 14, score: 3.7, anonimizado: false, fragmentos: 21, paginas: 9, formato: "DOCX",
    tags: ["Detox", "Android", "mobile", "E2E"],
  },
  {
    id: "TEC-visual-regression-2025-12-10",
    titulo: "Visual regression testing con Percy en pipelines productivos",
    carpeta: "TEC", tipo: "GUIA", autoritativo: true, estado: "vigente",
    autor: "Lucía Vargas", autorOid: AUTHOR_OIDS.lucia, rol: "Automation Engineer",
    fecha: "2025-12-10", revision: "2026-02-15", version: "2.0",
    citas: 22, score: 4.0, anonimizado: true, fragmentos: 24, paginas: 12, formato: "DOCX",
    aprobador: "Mateo Robles", fechaAprobacion: "2025-12-15",
    tags: ["Percy", "visual-regression", "CI/CD"],
  },
  {
    id: "TEC-load-testing-locust-2025-11-28",
    titulo: "Load testing con Locust sobre APIs GraphQL",
    carpeta: "TEC", tipo: "MTEC", autoritativo: false, estado: "vigente",
    autor: "Diego Castro", autorOid: AUTHOR_OIDS.diego, rol: "Performance Engineer",
    fecha: "2025-11-28", revision: "2025-11-28", version: "1.0",
    citas: 9, score: 3.5, anonimizado: true, fragmentos: 18, paginas: 8, formato: "DOCX",
    tags: ["Locust", "load-testing", "GraphQL"],
  },
  {
    id: "TEC-chaos-engineering-intro-2025-10-15",
    titulo: "Introducción a chaos engineering para QA",
    carpeta: "TEC", tipo: "GUIA", autoritativo: false, estado: "vigente",
    autor: "Tomás Iglesias", autorOid: AUTHOR_OIDS.tomas, rol: "QA Architect",
    fecha: "2025-10-15", revision: "2025-10-15", version: "1.0",
    citas: 6, score: 3.2, anonimizado: false, fragmentos: 15, paginas: 10, formato: "DOCX",
    tags: ["chaos-engineering", "resilience"],
  },
  {
    id: "TEC-mutation-testing-2025-09-08",
    titulo: "Mutation testing con Stryker para validar cobertura efectiva",
    carpeta: "TEC", tipo: "MTEC", autoritativo: true, estado: "vigente",
    autor: "Renata Soto", autorOid: AUTHOR_OIDS.renata, rol: "Test Engineer",
    fecha: "2025-09-08", revision: "2026-01-30", version: "1.2",
    citas: 19, score: 4.1, anonimizado: true, fragmentos: 28, paginas: 13, formato: "DOCX",
    aprobador: "Andrés Altamiranda", fechaAprobacion: "2025-09-12",
    tags: ["Stryker", "mutation-testing", "cobertura"],
  },
  {
    id: "TEC-test-pyramid-revisada-2025-08-20",
    titulo: "Test pyramid revisada para arquitecturas event-driven",
    carpeta: "TEC", tipo: "MTEC", autoritativo: true, estado: "obsoleto",
    autor: "Andrés Altamiranda", autorOid: AUTHOR_OIDS.andres, rol: "QA Architect",
    fecha: "2025-08-20", revision: "2025-08-20", version: "1.0",
    citas: 3, score: 2.9, anonimizado: false, fragmentos: 19, paginas: 11, formato: "DOCX",
    tags: ["test-pyramid", "event-driven", "deprecated"],
  },
  {
    id: "TEC-async-testing-patterns-2025-07-14",
    titulo: "Patrones de testing asíncrono en aplicaciones reactivas",
    carpeta: "TEC", tipo: "GUIA", autoritativo: false, estado: "vigente",
    autor: "Sofía Núñez", autorOid: AUTHOR_OIDS.sofia, rol: "Mobile QA",
    fecha: "2025-07-14", revision: "2025-09-22", version: "1.1",
    citas: 11, score: 3.6, anonimizado: false, fragmentos: 17, paginas: 9, formato: "DOCX",
    tags: ["async", "reactive", "RxJS"],
  },

  // PROC (8)
  {
    id: "PROC-incidentes-staging-2026-03-18",
    titulo: "Procedimiento de escalamiento ante caída de ambiente staging",
    carpeta: "PROC", tipo: "PROC", autoritativo: true, estado: "vigente",
    autor: "Camila Pereyra", autorOid: AUTHOR_OIDS.camila, rol: "Test Lead",
    fecha: "2026-03-18", revision: "2026-03-18", version: "2.0",
    citas: 31, score: 4.2, anonimizado: false, fragmentos: 22, paginas: 9, formato: "DOCX",
    aprobador: "Andrés Altamiranda", fechaAprobacion: "2026-03-20",
    tags: ["staging", "incidentes", "escalamiento"],
  },
  {
    id: "PROC-revision-codigo-2026-05-02",
    titulo: "Política de revisión de código y aprobación de PRs",
    carpeta: "PROC", tipo: "POL", autoritativo: true, estado: "vigente",
    autor: "Camila Pereyra", autorOid: AUTHOR_OIDS.camila, rol: "Test Lead",
    fecha: "2026-05-02", revision: "2026-05-02", version: "1.0",
    citas: 8, score: 4.0, anonimizado: false, fragmentos: 12, paginas: 6, formato: "DOCX",
    aprobador: "Andrés Altamiranda", fechaAprobacion: "2026-05-05",
    tags: ["code-review", "PR", "aprobación"],
  },
  {
    id: "PROC-release-canary-2026-02-08",
    titulo: "Proceso de release canary con gates de calidad automatizados",
    carpeta: "PROC", tipo: "PROC", autoritativo: true, estado: "vigente",
    autor: "Mateo Robles", autorOid: AUTHOR_OIDS.mateo, rol: "Automation Lead",
    fecha: "2026-02-08", revision: "2026-04-18", version: "1.4",
    citas: 24, score: 4.3, anonimizado: true, fragmentos: 31, paginas: 14, formato: "DOCX",
    aprobador: "Andrés Altamiranda", fechaAprobacion: "2026-02-11",
    tags: ["canary", "release", "quality-gates"],
  },
  {
    id: "PROC-onboarding-qa-2025-11-10",
    titulo: "Onboarding de nuevos QA en proyectos cliente",
    carpeta: "PROC", tipo: "GUIA", autoritativo: false, estado: "vigente",
    autor: "Lucía Vargas", autorOid: AUTHOR_OIDS.lucia, rol: "Automation Engineer",
    fecha: "2025-11-10", revision: "2026-03-01", version: "1.2",
    citas: 16, score: 3.8, anonimizado: false, fragmentos: 20, paginas: 11, formato: "DOCX",
    tags: ["onboarding", "QA", "training"],
  },
  {
    id: "PROC-handoff-dev-qa-2025-09-22",
    titulo: "Handoff entre desarrollo y QA con criterios de aceptación",
    carpeta: "PROC", tipo: "PROC", autoritativo: true, estado: "vigente",
    autor: "Camila Pereyra", autorOid: AUTHOR_OIDS.camila, rol: "Test Lead",
    fecha: "2025-09-22", revision: "2026-01-12", version: "2.1",
    citas: 21, score: 4.1, anonimizado: false, fragmentos: 18, paginas: 8, formato: "DOCX",
    aprobador: "Andrés Altamiranda", fechaAprobacion: "2025-09-25",
    tags: ["handoff", "DoR", "DoD"],
  },
  {
    id: "PROC-bug-triage-2025-07-30",
    titulo: "Procedimiento de bug triage semanal con priorización RICE",
    carpeta: "PROC", tipo: "PROC", autoritativo: false, estado: "en-revision",
    autor: "Renata Soto", autorOid: AUTHOR_OIDS.renata, rol: "Test Engineer",
    fecha: "2025-07-30", revision: "2026-04-05", version: "1.1",
    citas: 7, score: 3.4, anonimizado: false, fragmentos: 14, paginas: 7, formato: "DOCX",
    tags: ["bug-triage", "RICE", "priorización"],
  },
  {
    id: "PROC-test-data-management-2025-06-18",
    titulo: "Gestión de datos de prueba con anonimización automática",
    carpeta: "PROC", tipo: "POL", autoritativo: true, estado: "vigente",
    autor: "Andrés Altamiranda", autorOid: AUTHOR_OIDS.andres, rol: "GK Lead",
    fecha: "2025-06-18", revision: "2026-02-28", version: "2.0",
    citas: 33, score: 4.4, anonimizado: true, fragmentos: 26, paginas: 12, formato: "DOCX",
    aprobador: "Andrés Altamiranda", fechaAprobacion: "2025-06-22",
    tags: ["test-data", "anonimización", "GDPR"],
  },
  {
    id: "PROC-postmortem-template-2025-05-04",
    titulo: "Template de postmortem para incidentes productivos",
    carpeta: "PROC", tipo: "FORM", autoritativo: true, estado: "vigente",
    autor: "Camila Pereyra", autorOid: AUTHOR_OIDS.camila, rol: "Test Lead",
    fecha: "2025-05-04", revision: "2025-05-04", version: "1.0",
    citas: 18, score: 3.9, anonimizado: false, fragmentos: 11, paginas: 5, formato: "DOCX",
    aprobador: "Andrés Altamiranda", fechaAprobacion: "2025-05-07",
    tags: ["postmortem", "template", "incidentes"],
  },

  // ARQ (6)
  {
    id: "ARQ-microservicios-checkout-2026-02-11",
    titulo: "Arquitectura de pruebas en microservicios de checkout — Cliente C7",
    carpeta: "ARQ", tipo: "ARCL", autoritativo: true, estado: "vigente",
    autor: "Andrés Altamiranda", autorOid: AUTHOR_OIDS.andres, rol: "QA Architect",
    fecha: "2026-02-11", revision: "2026-04-02", version: "2.1",
    citas: 58, score: 4.7, anonimizado: true, fragmentos: 64, paginas: 28, formato: "DOCX",
    aprobador: "Andrés Altamiranda", fechaAprobacion: "2026-02-14",
    tags: ["microservicios", "checkout", "contract-testing"],
  },
  {
    id: "ARQ-event-driven-2026-01-08",
    titulo: "Testing en arquitecturas event-driven con Kafka y SQS",
    carpeta: "ARQ", tipo: "MTEC", autoritativo: true, estado: "vigente",
    autor: "Tomás Iglesias", autorOid: AUTHOR_OIDS.tomas, rol: "QA Architect",
    fecha: "2026-01-08", revision: "2026-03-18", version: "1.2",
    citas: 41, score: 4.5, anonimizado: true, fragmentos: 48, paginas: 22, formato: "DOCX",
    aprobador: "Andrés Altamiranda", fechaAprobacion: "2026-01-12",
    tags: ["event-driven", "Kafka", "SQS"],
  },
  {
    id: "ARQ-serverless-faas-2025-12-22",
    titulo: "Estrategia de testing en arquitecturas serverless FaaS",
    carpeta: "ARQ", tipo: "MTEC", autoritativo: true, estado: "vigente",
    autor: "Tomás Iglesias", autorOid: AUTHOR_OIDS.tomas, rol: "QA Architect",
    fecha: "2025-12-22", revision: "2025-12-22", version: "1.0",
    citas: 29, score: 4.3, anonimizado: true, fragmentos: 36, paginas: 18, formato: "DOCX",
    aprobador: "Andrés Altamiranda", fechaAprobacion: "2025-12-28",
    tags: ["serverless", "FaaS", "Lambda"],
  },
  {
    id: "ARQ-data-platform-2025-10-30",
    titulo: "Arquetipo de testing para data platforms con Snowflake",
    carpeta: "ARQ", tipo: "ARCL", autoritativo: true, estado: "vigente",
    autor: "Andrés Altamiranda", autorOid: AUTHOR_OIDS.andres, rol: "QA Architect",
    fecha: "2025-10-30", revision: "2026-02-08", version: "1.3",
    citas: 36, score: 4.4, anonimizado: true, fragmentos: 41, paginas: 19, formato: "DOCX",
    aprobador: "Andrés Altamiranda", fechaAprobacion: "2025-11-04",
    tags: ["data-platform", "Snowflake", "data-quality"],
  },
  {
    id: "ARQ-mobile-native-2025-08-12",
    titulo: "Arquitectura de testing mobile nativo iOS+Android compartido",
    carpeta: "ARQ", tipo: "MTEC", autoritativo: false, estado: "vigente",
    autor: "Sofía Núñez", autorOid: AUTHOR_OIDS.sofia, rol: "Mobile QA",
    fecha: "2025-08-12", revision: "2026-01-20", version: "1.1",
    citas: 17, score: 3.8, anonimizado: false, fragmentos: 25, paginas: 14, formato: "DOCX",
    tags: ["mobile", "iOS", "Android", "shared"],
  },
  {
    id: "ARQ-zero-trust-2025-06-05",
    titulo: "Testing de arquitecturas zero-trust con mTLS",
    carpeta: "ARQ", tipo: "MTEC", autoritativo: true, estado: "vigente",
    autor: "Andrés Altamiranda", autorOid: AUTHOR_OIDS.andres, rol: "QA Architect",
    fecha: "2025-06-05", revision: "2025-12-15", version: "1.4",
    citas: 25, score: 4.6, anonimizado: true, fragmentos: 32, paginas: 16, formato: "DOCX",
    aprobador: "Andrés Altamiranda", fechaAprobacion: "2025-06-10",
    tags: ["zero-trust", "mTLS", "security"],
  },

  // HERR (8)
  {
    id: "HERR-jmeter-baseline-2026-04-30",
    titulo: "Configuración de baselines de performance en JMeter para APIs REST",
    carpeta: "HERR", tipo: "INST", autoritativo: false, estado: "generado",
    autor: "Diego Castro", autorOid: AUTHOR_OIDS.diego, rol: "Performance Engineer",
    fecha: "2026-04-30", revision: "2026-04-30", version: "1.0",
    citas: 12, score: 3.4, anonimizado: true, fragmentos: 19, paginas: 11, formato: "DOCX",
    tags: ["JMeter", "performance", "baseline", "API"],
  },
  {
    id: "HERR-playwright-config-2026-03-25",
    titulo: "Configuración avanzada de Playwright con proyectos paralelos",
    carpeta: "HERR", tipo: "INST", autoritativo: true, estado: "vigente",
    autor: "Lucía Vargas", autorOid: AUTHOR_OIDS.lucia, rol: "Automation Engineer",
    fecha: "2026-03-25", revision: "2026-04-30", version: "1.1",
    citas: 19, score: 4.1, anonimizado: false, fragmentos: 23, paginas: 12, formato: "DOCX",
    aprobador: "Mateo Robles", fechaAprobacion: "2026-03-28",
    tags: ["Playwright", "configuración", "paralelización"],
  },
  {
    id: "HERR-postman-collections-2026-02-20",
    titulo: "Gestión de colecciones Postman con Newman en CI",
    carpeta: "HERR", tipo: "GUIA", autoritativo: false, estado: "vigente",
    autor: "Sofía Núñez", autorOid: AUTHOR_OIDS.sofia, rol: "Mobile QA",
    fecha: "2026-02-20", revision: "2026-02-20", version: "1.0",
    citas: 8, score: 3.3, anonimizado: false, fragmentos: 14, paginas: 7, formato: "DOCX",
    tags: ["Postman", "Newman", "CI"],
  },
  {
    id: "HERR-selenium-grid-2025-11-15",
    titulo: "Despliegue de Selenium Grid 4 en Kubernetes",
    carpeta: "HERR", tipo: "INST", autoritativo: true, estado: "vigente",
    autor: "Mateo Robles", autorOid: AUTHOR_OIDS.mateo, rol: "Automation Lead",
    fecha: "2025-11-15", revision: "2026-02-08", version: "1.2",
    citas: 23, score: 4.0, anonimizado: true, fragmentos: 27, paginas: 13, formato: "DOCX",
    aprobador: "Andrés Altamiranda", fechaAprobacion: "2025-11-18",
    tags: ["Selenium", "Grid", "Kubernetes"],
  },
  {
    id: "HERR-allure-reports-2025-09-12",
    titulo: "Reportes Allure consolidados para suites multi-framework",
    carpeta: "HERR", tipo: "GUIA", autoritativo: false, estado: "vigente",
    autor: "Renata Soto", autorOid: AUTHOR_OIDS.renata, rol: "Test Engineer",
    fecha: "2025-09-12", revision: "2025-09-12", version: "1.0",
    citas: 11, score: 3.6, anonimizado: false, fragmentos: 16, paginas: 8, formato: "DOCX",
    tags: ["Allure", "reportes", "multi-framework"],
  },
  {
    id: "HERR-k6-cloud-2025-07-25",
    titulo: "Pruebas de carga distribuidas con k6 Cloud",
    carpeta: "HERR", tipo: "MTEC", autoritativo: false, estado: "vigente",
    autor: "Diego Castro", autorOid: AUTHOR_OIDS.diego, rol: "Performance Engineer",
    fecha: "2025-07-25", revision: "2025-12-08", version: "1.1",
    citas: 14, score: 3.7, anonimizado: true, fragmentos: 22, paginas: 11, formato: "DOCX",
    tags: ["k6", "load-testing", "cloud"],
  },
  {
    id: "HERR-zap-baseline-2025-05-30",
    titulo: "Baseline OWASP ZAP integrado en pipelines de pre-deploy",
    carpeta: "HERR", tipo: "INST", autoritativo: true, estado: "vigente",
    autor: "Tomás Iglesias", autorOid: AUTHOR_OIDS.tomas, rol: "QA Architect",
    fecha: "2025-05-30", revision: "2026-01-15", version: "1.3",
    citas: 27, score: 4.2, anonimizado: false, fragmentos: 29, paginas: 14, formato: "DOCX",
    aprobador: "Andrés Altamiranda", fechaAprobacion: "2025-06-04",
    tags: ["OWASP", "ZAP", "security", "DAST"],
  },
  {
    id: "HERR-browserstack-2025-04-08",
    titulo: "Estrategia de cross-browser testing con BrowserStack",
    carpeta: "HERR", tipo: "GUIA", autoritativo: false, estado: "obsoleto",
    autor: "Sofía Núñez", autorOid: AUTHOR_OIDS.sofia, rol: "Mobile QA",
    fecha: "2025-04-08", revision: "2025-04-08", version: "1.0",
    citas: 4, score: 2.8, anonimizado: false, fragmentos: 13, paginas: 6, formato: "DOCX",
    tags: ["BrowserStack", "cross-browser", "deprecated"],
  },

  // NEG (4)
  {
    id: "NEG-criterios-go-nogo-2026-01-29",
    titulo: "Criterios de Go/No-Go para releases con riesgo regulatorio",
    carpeta: "NEG", tipo: "POL", autoritativo: true, estado: "vigente",
    autor: "Camila Pereyra", autorOid: AUTHOR_OIDS.camila, rol: "Test Lead",
    fecha: "2026-01-29", revision: "2026-04-15", version: "3.0",
    citas: 39, score: 4.5, anonimizado: false, fragmentos: 17, paginas: 8, formato: "DOCX",
    aprobador: "Andrés Altamiranda", fechaAprobacion: "2026-02-01",
    tags: ["regulatorio", "go-no-go", "release"],
  },
  {
    id: "NEG-sla-clientes-2026-03-12",
    titulo: "SLAs de QA para clientes enterprise tier A",
    carpeta: "NEG", tipo: "POL", autoritativo: true, estado: "vigente",
    autor: "Andrés Altamiranda", autorOid: AUTHOR_OIDS.andres, rol: "GK Lead",
    fecha: "2026-03-12", revision: "2026-03-12", version: "1.0",
    citas: 18, score: 4.1, anonimizado: true, fragmentos: 15, paginas: 7, formato: "DOCX",
    aprobador: "Andrés Altamiranda", fechaAprobacion: "2026-03-15",
    tags: ["SLA", "enterprise", "tier-A"],
  },
  {
    id: "NEG-pricing-qaas-2025-10-08",
    titulo: "Estructura de pricing del modelo QaaS por unidad de capacidad",
    carpeta: "NEG", tipo: "POL", autoritativo: true, estado: "vigente",
    autor: "Andrés Altamiranda", autorOid: AUTHOR_OIDS.andres, rol: "GK Lead",
    fecha: "2025-10-08", revision: "2026-02-20", version: "1.2",
    citas: 26, score: 4.3, anonimizado: false, fragmentos: 19, paginas: 10, formato: "DOCX",
    aprobador: "Andrés Altamiranda", fechaAprobacion: "2025-10-12",
    tags: ["QaaS", "pricing", "comercial"],
  },
  {
    id: "NEG-arquetipo-cliente-fintech-2025-08-28",
    titulo: "Arquetipo de cliente fintech con regulaciones BCRA",
    carpeta: "NEG", tipo: "ARCL", autoritativo: true, estado: "vigente",
    autor: "Camila Pereyra", autorOid: AUTHOR_OIDS.camila, rol: "Test Lead",
    fecha: "2025-08-28", revision: "2026-01-10", version: "1.1",
    citas: 22, score: 4.0, anonimizado: true, fragmentos: 24, paginas: 13, formato: "DOCX",
    aprobador: "Andrés Altamiranda", fechaAprobacion: "2025-09-01",
    tags: ["fintech", "BCRA", "regulatorio"],
  },

  // ENV (4)
  {
    id: "ENV-staging-refresh-2026-04-10",
    titulo: "Refresh quincenal de datos en staging desde producción anonimizada",
    carpeta: "ENV", tipo: "PROC", autoritativo: true, estado: "vigente",
    autor: "Diego Castro", autorOid: AUTHOR_OIDS.diego, rol: "Performance Engineer",
    fecha: "2026-04-10", revision: "2026-04-10", version: "1.0",
    citas: 13, score: 3.9, anonimizado: true, fragmentos: 14, paginas: 6, formato: "DOCX",
    aprobador: "Camila Pereyra", fechaAprobacion: "2026-04-12",
    tags: ["staging", "data-refresh", "anonimización"],
  },
  {
    id: "ENV-feature-flags-2026-02-25",
    titulo: "Estrategia de feature flags por ambiente con LaunchDarkly",
    carpeta: "ENV", tipo: "GUIA", autoritativo: false, estado: "vigente",
    autor: "Mateo Robles", autorOid: AUTHOR_OIDS.mateo, rol: "Automation Lead",
    fecha: "2026-02-25", revision: "2026-02-25", version: "1.0",
    citas: 9, score: 3.5, anonimizado: false, fragmentos: 16, paginas: 8, formato: "DOCX",
    tags: ["feature-flags", "LaunchDarkly", "ambientes"],
  },
  {
    id: "ENV-blue-green-2025-12-05",
    titulo: "Despliegue blue-green con testing en pre-switch",
    carpeta: "ENV", tipo: "PROC", autoritativo: true, estado: "vigente",
    autor: "Tomás Iglesias", autorOid: AUTHOR_OIDS.tomas, rol: "QA Architect",
    fecha: "2025-12-05", revision: "2026-03-18", version: "1.2",
    citas: 17, score: 4.0, anonimizado: true, fragmentos: 18, paginas: 9, formato: "DOCX",
    aprobador: "Andrés Altamiranda", fechaAprobacion: "2025-12-08",
    tags: ["blue-green", "deploy", "pre-switch"],
  },
  {
    id: "ENV-secrets-vault-2025-09-30",
    titulo: "Gestión de secretos en ambientes con HashiCorp Vault",
    carpeta: "ENV", tipo: "INST", autoritativo: true, estado: "vigente",
    autor: "Diego Castro", autorOid: AUTHOR_OIDS.diego, rol: "Performance Engineer",
    fecha: "2025-09-30", revision: "2026-02-15", version: "1.1",
    citas: 15, score: 3.8, anonimizado: false, fragmentos: 20, paginas: 11, formato: "DOCX",
    aprobador: "Andrés Altamiranda", fechaAprobacion: "2025-10-03",
    tags: ["secrets", "Vault", "security"],
  },

  // EST (3)
  {
    id: "EST-naming-tests-2026-01-15",
    titulo: "Estándar de naming para casos de prueba automatizados",
    carpeta: "EST", tipo: "POL", autoritativo: true, estado: "vigente",
    autor: "Andrés Altamiranda", autorOid: AUTHOR_OIDS.andres, rol: "GK Lead",
    fecha: "2026-01-15", revision: "2026-04-20", version: "1.3",
    citas: 42, score: 4.7, anonimizado: false, fragmentos: 13, paginas: 6, formato: "DOCX",
    aprobador: "Andrés Altamiranda", fechaAprobacion: "2026-01-18",
    tags: ["estándares", "naming", "automation"],
  },
  {
    id: "EST-cobertura-minima-2025-11-22",
    titulo: "Política de cobertura mínima por capa de la pirámide",
    carpeta: "EST", tipo: "POL", autoritativo: true, estado: "vigente",
    autor: "Andrés Altamiranda", autorOid: AUTHOR_OIDS.andres, rol: "GK Lead",
    fecha: "2025-11-22", revision: "2026-02-28", version: "2.0",
    citas: 38, score: 4.6, anonimizado: false, fragmentos: 11, paginas: 5, formato: "DOCX",
    aprobador: "Andrés Altamiranda", fechaAprobacion: "2025-11-25",
    tags: ["cobertura", "pyramid", "estándar"],
  },
  {
    id: "EST-definicion-listo-2025-07-10",
    titulo: "Definición de Listo (DoR) y Hecho (DoD) para historias",
    carpeta: "EST", tipo: "POL", autoritativo: true, estado: "vigente",
    autor: "Camila Pereyra", autorOid: AUTHOR_OIDS.camila, rol: "Test Lead",
    fecha: "2025-07-10", revision: "2026-01-08", version: "1.2",
    citas: 31, score: 4.5, anonimizado: false, fragmentos: 14, paginas: 7, formato: "DOCX",
    aprobador: "Andrés Altamiranda", fechaAprobacion: "2025-07-14",
    tags: ["DoR", "DoD", "estándar"],
  },

  // CONT (2)
  {
    id: "CONT-cliente-c12-fintech-2025-12-18",
    titulo: "Contexto del cliente C12 — fintech regulada por SEC",
    carpeta: "CONT", tipo: "ARCL", autoritativo: false, estado: "vigente",
    autor: "Camila Pereyra", autorOid: AUTHOR_OIDS.camila, rol: "Test Lead",
    fecha: "2025-12-18", revision: "2026-03-08", version: "1.1",
    citas: 6, score: 3.2, anonimizado: true, fragmentos: 17, paginas: 9, formato: "DOCX",
    tags: ["cliente", "C12", "fintech", "SEC"],
  },
  {
    id: "CONT-vertical-retail-2025-06-22",
    titulo: "Vertical retail — patrones comunes de testing",
    carpeta: "CONT", tipo: "UEN", autoritativo: false, estado: "en-revision",
    autor: "Tomás Iglesias", autorOid: AUTHOR_OIDS.tomas, rol: "QA Architect",
    fecha: "2025-06-22", revision: "2026-04-12", version: "1.0",
    citas: 5, score: 3.0, anonimizado: false, fragmentos: 12, paginas: 6, formato: "DOCX",
    tags: ["retail", "vertical", "patrones"],
  },
];

/**
 * Citaciones recibidas por documentos del catálogo. Stub que devuelve
 * `DocumentDetail` cuando la UI pide `/explorer/[docId]`. En backend Fase 3
 * (RAG) lo genera al indexar el doc origen.
 *
 * Solo se pueblan algunas piezas representativas — los demás docs devuelven
 * `incomingCitations: []`.
 */
export const INCOMING_CITATIONS: Record<string, IncomingCitation[]> = {
  "ARQ-microservicios-checkout-2026-02-11": [
    {
      sourceDocId: "TEC-api-contract-testing-2026-02-28",
      sourceTitle: "Contract testing con Pact entre microservicios de pagos",
      sourceFolder: "TEC",
      section: "§4 — Adopción organizacional",
      snippet: "Como referencia de arquitecturas similares, ver [ARQ-microservicios-checkout-2026-02-11]…",
      citedAt: "2026-02-28",
    },
    {
      sourceDocId: "ARQ-event-driven-2026-01-08",
      sourceTitle: "Testing en arquitecturas event-driven con Kafka y SQS",
      sourceFolder: "ARQ",
      section: "§2 — Casos de uso",
      snippet: "El caso checkout descripto en [ARQ-microservicios-checkout] ilustra…",
      citedAt: "2026-01-08",
    },
  ],
  "TEC-flakiness-detection-2026-04-22": [
    {
      sourceDocId: "PROC-revision-codigo-2026-05-02",
      sourceTitle: "Política de revisión de código y aprobación de PRs",
      sourceFolder: "PROC",
      section: "§3 — Bloqueo de PR",
      snippet: "Si la suite presenta flakiness conocido (ver [TEC-flakiness-detection])…",
      citedAt: "2026-05-02",
    },
  ],
  "EST-naming-tests-2026-01-15": [
    {
      sourceDocId: "TEC-data-driven-cypress-2026-03-05",
      sourceTitle: "Estrategia data-driven en Cypress con fixtures versionadas",
      sourceFolder: "TEC",
      section: "§5 — Buenas prácticas",
      snippet: "Aplicar el naming definido en [EST-naming-tests-2026-01-15]…",
      citedAt: "2026-03-05",
    },
    {
      sourceDocId: "TEC-api-contract-testing-2026-02-28",
      sourceTitle: "Contract testing con Pact entre microservicios de pagos",
      sourceFolder: "TEC",
      section: "§3 — Convenciones",
      snippet: "Naming de contracts según [EST-naming-tests]…",
      citedAt: "2026-02-28",
    },
    {
      sourceDocId: "HERR-playwright-config-2026-03-25",
      sourceTitle: "Configuración avanzada de Playwright con proyectos paralelos",
      sourceFolder: "HERR",
      section: "§2 — Estructura",
      snippet: "Tests nombrados según [EST-naming-tests-2026-01-15]…",
      citedAt: "2026-03-25",
    },
  ],
};

/**
 * Resúmenes ejecutivos por documento. En backend Fase 4 (generadores) se
 * extraen del primer párrafo del DOCX; acá los hardcodeamos para que la UI
 * del detalle tenga contenido representativo.
 */
export const DOCUMENT_RESUMES: Record<string, string> = {
  "ARQ-microservicios-checkout-2026-02-11":
    "Arquetipo de testing para microservicios de checkout en cliente enterprise. Cubre contract testing entre 12 servicios, simulación de gateways de pago externos y validación end-to-end con load realista. Base para implementaciones similares en el vertical e-commerce.",
  "TEC-flakiness-detection-2026-04-22":
    "Sistemática para detectar tests inestables en la suite de regresión: análisis estadístico sobre 30 corridas, marcado de cuarentena automático, dashboard de seguimiento y reglas de re-incorporación a la suite principal. Reduce el ruido del CI ~70%.",
  "EST-naming-tests-2026-01-15":
    "Estándar global de naming para casos automatizados: estructura jerárquica describe/context/it, prefijos por tipo de test (unit/integration/e2e), nomenclatura de fixtures y mocks. Aplicable transversalmente a JS, Python y Java.",
};

export const MOCK_HOT_TOPICS: HotTopic[] = [
  { topic: "Flakiness en pipelines de CI", queries30d: 87, citationCount: 14, isGap: false },
  { topic: "Contract testing con Pact", queries30d: 64, citationCount: 9, isGap: false },
  { topic: "Performance testing con k6", queries30d: 52, citationCount: 4, isGap: true },
  { topic: "Testing de microservicios", queries30d: 48, citationCount: 12, isGap: false },
  { topic: "Anonimización de datos productivos", queries30d: 41, citationCount: 6, isGap: false },
  { topic: "Mobile native testing", queries30d: 38, citationCount: 3, isGap: true },
  { topic: "Naming de casos de prueba", queries30d: 35, citationCount: 11, isGap: false },
  { topic: "Chaos engineering aplicado a QA", queries30d: 22, citationCount: 1, isGap: true },
];

export const MOCK_RECENT_ACTIVITY: RecentActivityItem[] = [
  {
    id: "act-001",
    type: "captura",
    actor: { oid: AUTHOR_OIDS.lucia, name: "Lucía Vargas" },
    at: "2026-05-19T13:22:00.000Z",
    summary: "Capturó memoria técnica sobre detección de flakiness en suite Playwright",
    refUrl: "/explorer/TEC-flakiness-detection-2026-04-22",
  },
  {
    id: "act-002",
    type: "ingesta",
    actor: { oid: AUTHOR_OIDS.camila, name: "Camila Pereyra" },
    at: "2026-05-19T11:08:00.000Z",
    summary: "Aprobó ingesta del documento 'Política de revisión de código' v1.0",
    refUrl: "/explorer/PROC-revision-codigo-2026-05-02",
  },
  {
    id: "act-003",
    type: "consulta",
    actor: { oid: AUTHOR_OIDS.diego, name: "Diego Castro" },
    at: "2026-05-19T09:45:00.000Z",
    summary: "Consultó 5 documentos sobre performance testing con k6 y Locust",
  },
  {
    id: "act-004",
    type: "taxonomia",
    actor: { oid: AUTHOR_OIDS.andres, name: "Andrés Altamiranda" },
    at: "2026-05-18T17:30:00.000Z",
    summary: "Agregó tag 'chaos-engineering' a la taxonomía global",
  },
  {
    id: "act-005",
    type: "captura",
    actor: { oid: AUTHOR_OIDS.tomas, name: "Tomás Iglesias" },
    at: "2026-05-18T14:12:00.000Z",
    summary: "Capturó arquetipo de testing en event-driven con Kafka",
    refUrl: "/explorer/ARQ-event-driven-2026-01-08",
  },
  {
    id: "act-006",
    type: "consulta",
    actor: { oid: AUTHOR_OIDS.sofia, name: "Sofía Núñez" },
    at: "2026-05-18T10:55:00.000Z",
    summary: "Buscó documentación sobre testing mobile híbrido",
  },
  {
    id: "act-007",
    type: "ingesta",
    actor: { oid: AUTHOR_OIDS.renata, name: "Renata Soto" },
    at: "2026-05-17T16:40:00.000Z",
    summary: "Subió 'Procedimiento de bug triage' a la bandeja de ingesta",
  },
  {
    id: "act-008",
    type: "captura",
    actor: { oid: AUTHOR_OIDS.mateo, name: "Mateo Robles" },
    at: "2026-05-17T11:20:00.000Z",
    summary: "Actualizó guía de release canary a v1.4 con gates automatizados",
    refUrl: "/explorer/PROC-release-canary-2026-02-08",
  },
  {
    id: "act-009",
    type: "taxonomia",
    actor: { oid: AUTHOR_OIDS.andres, name: "Andrés Altamiranda" },
    at: "2026-05-16T15:05:00.000Z",
    summary: "Marcó como obsoleto el documento 'Test pyramid revisada para event-driven'",
    refUrl: "/explorer/TEC-test-pyramid-revisada-2025-08-20",
  },
  {
    id: "act-010",
    type: "consulta",
    actor: { oid: AUTHOR_OIDS.lucia, name: "Lucía Vargas" },
    at: "2026-05-16T09:30:00.000Z",
    summary: "Consultó política de cobertura mínima por capa",
  },
  {
    id: "act-011",
    type: "captura",
    actor: { oid: AUTHOR_OIDS.camila, name: "Camila Pereyra" },
    at: "2026-05-15T17:15:00.000Z",
    summary: "Capturó procedimiento de escalamiento ante caída de staging",
    refUrl: "/explorer/PROC-incidentes-staging-2026-03-18",
  },
  {
    id: "act-012",
    type: "ingesta",
    actor: { oid: AUTHOR_OIDS.diego, name: "Diego Castro" },
    at: "2026-05-15T13:00:00.000Z",
    summary: "Pendiente: 'Plantilla de baselines JMeter' esperando metadata",
  },
];

export const INGESTION_PENDING: IngestionItem[] = [
  {
    id: "p1",
    filename: "Politica_Seguridad_QA_v3.docx",
    size: "2.4 MB",
    paginas: 22,
    sugerido: { carpeta: "EST", tipo: "POL" },
    aprobador: "",
    fechaAprobacion: "",
    fuenteOriginal: "",
    version: "",
    estado: "pendiente-metadata",
  },
  {
    id: "p2",
    filename: "Plantilla-Casos-Aceptacion-Aliantia.xlsx",
    size: "640 KB",
    paginas: 1,
    sugerido: { carpeta: "PROC", tipo: "FORM" },
    aprobador: "Andrés Altamiranda",
    fechaAprobacion: "2026-05-02",
    fuenteOriginal: "SharePoint/QA/Plantillas/",
    version: "1.4",
    estado: "listo",
  },
];

export const GK_KPIS = {
  capturas30: { value: 142, delta: "+18% vs mes anterior", tone: "pass" as const },
  consultas30: { value: "3.1k", delta: "+24%", tone: "pass" as const },
  finalizacion: { value: "78%", delta: "+4 pp", tone: "pass" as const },
  sinResultado: { value: "9.2%", delta: "-3 pp", tone: "pass" as const },
  autoritativos: { value: "62%", delta: "+5 pp", tone: "pass" as const },
  scorePromedio: { value: 3.94, delta: "+0.12", tone: "pass" as const },
};
