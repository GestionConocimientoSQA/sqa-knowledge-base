/**
 * Configuración Playwright para los E2E del frontend.
 *
 * Estrategia:
 *  - `webServer` arranca `pnpm dev` automáticamente y espera a que el puerto
 *    3000 responda. En CI lo construimos primero y servimos con `pnpm start`.
 *  - 1 proyecto chromium por defecto (rápido). Firefox y webkit quedan como
 *    opt-in en CI con flag (`--project=firefox`) — no agregan valor en cada
 *    corrida local porque la mayor parte de los bugs cross-browser de Next 15
 *    son raros.
 *  - Tests aislados: cada test arranca con localStorage limpio (sin sesión
 *    persistida). Helpers en `e2e/fixtures/` resetean estado.
 *  - Tracing: `on-first-retry` por defecto — sin overhead si el test pasa.
 */
import { defineConfig, devices } from "@playwright/test";

const isCI = !!process.env.CI;
const PORT = Number(process.env.E2E_PORT ?? 3100);
const BASE_URL = `http://localhost:${PORT}`;

export default defineConfig({
  testDir: "./e2e",
  timeout: 30_000,
  expect: { timeout: 5_000 },
  // Dev server compartido — workers paralelos generan races sobre la URL
  // y el localStorage. Forzamos 1 worker tanto local como en CI; los tests
  // son rápidos (~20s la suite completa) y la confiabilidad importa más.
  fullyParallel: false,
  forbidOnly: isCI,
  retries: isCI ? 2 : 0,
  workers: 1,
  reporter: isCI
    ? [["list"], ["html", { open: "never", outputFolder: "playwright-report" }]]
    : "list",
  use: {
    baseURL: BASE_URL,
    trace: "on-first-retry",
    screenshot: "only-on-failure",
    video: isCI ? "retain-on-failure" : "off",
    actionTimeout: 5_000,
    navigationTimeout: 10_000,
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
    // Habilitar manualmente con `pnpm test:e2e --project=firefox` cuando haga falta.
    // {
    //   name: "firefox",
    //   use: { ...devices["Desktop Firefox"] },
    // },
  ],
  webServer: {
    command: `pnpm dev --port ${PORT}`,
    url: BASE_URL,
    reuseExistingServer: !isCI,
    timeout: 120_000,
    stdout: "ignore",
    stderr: "pipe",
  },
});
