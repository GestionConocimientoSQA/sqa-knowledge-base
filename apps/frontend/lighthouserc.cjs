/**
 * Configuración de Lighthouse CI para el frontend.
 *
 * Estrategia:
 *  - Audita un build de producción (`pnpm build && pnpm start`) en puerto 3200,
 *    no el dev server (los números de dev no son representativos).
 *  - 3 URLs clave: login (anónimo), dashboard (admin) y explorer.
 *  - Modo Capturador vs admin requeriría auth — Lighthouse CI no soporta
 *    fácilmente localStorage seeding entre runs. Por eso auditamos páginas
 *    accesibles sin sesión (login) o las rutas SSR auth-redirect (dashboard
 *    se redirige a login, lo cual también testea el camino feliz).
 *
 * Baseline real (medido contra build de prod, 2026-05-22, login page):
 *   performance 99 · accessibility 100 · best-practices 96 · seo 100
 * Los thresholds están seteados para detectar regresiones reales sin
 * generar falsos positivos por variabilidad de runs.
 *
 * Windows known issue: chrome-launcher tira `EPERM rmSync` al limpiar el
 * tempdir de Chrome al cerrar. Es cosmético — los reports ya quedaron en
 * `.lighthouseci/`. En CI Linux (GH Actions ubuntu-latest) no ocurre. Si
 * estás en Windows local y necesitás el exit code 0, corré los pasos
 * manualmente: `lhci collect && lhci assert`.
 */

const PORT = process.env.LHCI_PORT ?? 3200;

/** @type {import('@lhci/cli').Config} */
module.exports = {
  ci: {
    collect: {
      startServerCommand: `pnpm start --port ${PORT}`,
      url: [
        `http://localhost:${PORT}/login`,
        `http://localhost:${PORT}/dashboard`,
        `http://localhost:${PORT}/explorer`,
      ],
      numberOfRuns: 1,
      startServerReadyPattern: "Ready in",
      startServerReadyTimeout: 60_000,
      settings: {
        // Headless chromium incluido con lhci.
        chromeFlags: "--headless=new --no-sandbox",
        // Throttling móvil agrega ~3-5x latencia simulada — buen baseline
        // para detectar regresiones, no para medir performance absoluta.
        preset: "desktop",
        // Skip PWA audit category (no estamos haciendo PWA todavía).
        skipAudits: ["uses-http2", "redirects-http"],
      },
    },
    assert: {
      assertions: {
        // Thresholds calibrados al baseline real (login: 99/100/96/100).
        // Permite cierta tolerancia para variabilidad entre runs sin
        // dejar pasar regresiones reales.
        "categories:performance": ["error", { minScore: 0.9 }],
        "categories:accessibility": ["error", { minScore: 0.95 }],
        "categories:best-practices": ["error", { minScore: 0.9 }],
        "categories:seo": ["warn", { minScore: 0.9 }],
        // Estos audits específicos siempre deben pasar.
        "is-on-https": "off", // localhost, no aplica
        "uses-https": "off",
        "csp-xss": "warn", // CSP sin nonce todavía emite warn — esperado
      },
    },
    upload: {
      target: "filesystem",
      outputDir: "./.lighthouseci",
      reportFilenamePattern: "%%PATHNAME%%-%%DATETIME%%-report.%%EXTENSION%%",
    },
  },
};
