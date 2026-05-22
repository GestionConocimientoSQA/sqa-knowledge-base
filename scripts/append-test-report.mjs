#!/usr/bin/env node
/**
 * Append a row per test suite to docs/test-reports/test-runs.xlsx.
 *
 * Uso:
 *   node scripts/append-test-report.mjs \
 *     --suite=unit \
 *     --total=220 --passed=220 --failed=0 \
 *     --duration=16.23 \
 *     [--notes="comentario opcional"]
 *
 * O leyendo del JSON output de Vitest/Playwright:
 *   pnpm --filter @sqa/frontend test --reporter=json --outputFile=.test-run.json
 *   node scripts/append-test-report.mjs --suite=unit --from-vitest=apps/frontend/.test-run.json
 *
 *   pnpm --filter @sqa/frontend exec playwright test --reporter=json > apps/frontend/.e2e-run.json
 *   node scripts/append-test-report.mjs --suite=e2e --from-playwright=apps/frontend/.e2e-run.json
 *
 * El archivo se crea si no existe. Cada corrida es una fila — no se borra
 * histórico. Columnas: fecha · branch · commit · suite · total · pasados ·
 * fallados · duración (s) · notas.
 *
 * Directiva del usuario [[feedback-xlsx-reportes-pruebas]] — solo en
 * corridas completas/de cierre, no cada `pnpm test` interno.
 */

import { execSync } from "node:child_process";
import { existsSync, mkdirSync, readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import ExcelJS from "exceljs";

const __dirname = dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = resolve(__dirname, "..");
const OUTPUT_PATH = resolve(REPO_ROOT, "docs/test-reports/test-runs.xlsx");

/** Parsea flags `--key=value` y `--key value`. */
function parseArgs(argv) {
  const args = {};
  for (let i = 0; i < argv.length; i++) {
    const token = argv[i];
    if (!token.startsWith("--")) continue;
    const eq = token.indexOf("=");
    if (eq > -1) {
      args[token.slice(2, eq)] = token.slice(eq + 1);
    } else {
      args[token.slice(2)] = argv[i + 1] && !argv[i + 1].startsWith("--") ? argv[++i] : "true";
    }
  }
  return args;
}

function readGit(cmd) {
  try {
    return execSync(cmd, { cwd: REPO_ROOT, encoding: "utf8" }).trim();
  } catch {
    return "unknown";
  }
}

/**
 * Resumen desde el JSON de Vitest (`--reporter=json --outputFile=...`).
 * Estructura: { numTotalTests, numPassedTests, numFailedTests, startTime, ... }
 */
function summarizeVitest(jsonPath) {
  const data = JSON.parse(readFileSync(jsonPath, "utf8"));
  const total = data.numTotalTests ?? 0;
  const passed = data.numPassedTests ?? 0;
  const failed = data.numFailedTests ?? 0;
  // Vitest emite `startTime` y los `testResults[].endTime` (ms). Duración
  // total = max(endTime) - startTime.
  let durationMs = 0;
  if (data.startTime && Array.isArray(data.testResults)) {
    const ends = data.testResults
      .map((r) => r.endTime ?? 0)
      .filter((t) => t > 0);
    if (ends.length > 0) durationMs = Math.max(...ends) - data.startTime;
  }
  return { total, passed, failed, duration: +(durationMs / 1000).toFixed(2) };
}

/**
 * Resumen desde el JSON de Playwright (`--reporter=json`).
 * Estructura: { stats: { expected, unexpected, skipped, flaky, duration }, suites: [...] }
 */
function summarizePlaywright(jsonPath) {
  const data = JSON.parse(readFileSync(jsonPath, "utf8"));
  const stats = data.stats ?? {};
  const total =
    (stats.expected ?? 0) +
    (stats.unexpected ?? 0) +
    (stats.skipped ?? 0) +
    (stats.flaky ?? 0);
  const passed = stats.expected ?? 0;
  const failed = stats.unexpected ?? 0;
  const duration = +(((stats.duration ?? 0) / 1000)).toFixed(2);
  return { total, passed, failed, duration };
}

const HEADERS = [
  { header: "Fecha", key: "fecha", width: 19 },
  { header: "Branch", key: "branch", width: 28 },
  { header: "Commit", key: "commit", width: 12 },
  { header: "Suite", key: "suite", width: 14 },
  { header: "Total", key: "total", width: 8 },
  { header: "Pasados", key: "passed", width: 10 },
  { header: "Fallados", key: "failed", width: 10 },
  { header: "Duración (s)", key: "duration", width: 14 },
  { header: "Notas", key: "notes", width: 60 },
];

async function loadOrCreateWorkbook() {
  const wb = new ExcelJS.Workbook();
  const exists = existsSync(OUTPUT_PATH);
  if (exists) {
    await wb.xlsx.readFile(OUTPUT_PATH);
  }
  let sheet = wb.getWorksheet("Resumen");
  if (!sheet) {
    sheet = wb.addWorksheet("Resumen", {
      views: [{ state: "frozen", ySplit: 1 }],
    });
    sheet.columns = HEADERS;
    sheet.getRow(1).font = { bold: true };
    sheet.getRow(1).fill = {
      type: "pattern",
      pattern: "solid",
      fgColor: { argb: "FFE8EFF7" },
    };
  } else {
    // Sheet preexistente: NO re-setear `sheet.columns` — exceljs trunca
    // las filas ya escritas al reasignar el array completo. Sólo mutamos
    // el `key` de cada column in-place para que `addRow(objeto)` mapee
    // a las columnas correctas usando los keys de HEADERS.
    sheet.columns.forEach((col, i) => {
      const expected = HEADERS[i]?.key;
      if (expected) col.key = expected;
    });
  }
  return { wb, sheet };
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const suite = args.suite;
  if (!suite) {
    console.error("Falta --suite=<unit|e2e|lighthouse|...>");
    process.exit(1);
  }

  let metrics = { total: 0, passed: 0, failed: 0, duration: 0 };

  if (args["from-vitest"]) {
    metrics = summarizeVitest(resolve(REPO_ROOT, args["from-vitest"]));
  } else if (args["from-playwright"]) {
    metrics = summarizePlaywright(resolve(REPO_ROOT, args["from-playwright"]));
  } else {
    metrics = {
      total: Number(args.total ?? 0),
      passed: Number(args.passed ?? 0),
      failed: Number(args.failed ?? 0),
      duration: Number(args.duration ?? 0),
    };
  }

  const branch = readGit("git rev-parse --abbrev-ref HEAD");
  const commit = readGit("git rev-parse --short HEAD");
  const fecha = new Date().toISOString().replace("T", " ").slice(0, 19);
  const notes = args.notes ?? "";

  // Asegurar que el directorio padre exista.
  mkdirSync(dirname(OUTPUT_PATH), { recursive: true });

  const { wb, sheet } = await loadOrCreateWorkbook();
  const row = sheet.addRow({
    fecha,
    branch,
    commit,
    suite,
    total: metrics.total,
    passed: metrics.passed,
    failed: metrics.failed,
    duration: metrics.duration,
    notes,
  });
  // Resaltar filas con fallos en rojo claro.
  if (metrics.failed > 0) {
    row.fill = {
      type: "pattern",
      pattern: "solid",
      fgColor: { argb: "FFFCE4E4" },
    };
  }

  await wb.xlsx.writeFile(OUTPUT_PATH);
  console.log(
    `[test-report] ${suite}: ${metrics.passed}/${metrics.total} passed (${metrics.duration}s) → ${OUTPUT_PATH}`,
  );
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
