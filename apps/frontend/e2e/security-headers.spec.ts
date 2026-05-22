import { test, expect } from "@playwright/test";

/**
 * Verifica que los headers de seguridad estén presentes en todas las
 * páginas — defensa en profundidad contra XSS, clickjacking, mixed
 * content, MIME sniffing y data leakage por referer.
 */

const REQUIRED_HEADERS: Record<string, RegExp> = {
  "content-security-policy": /default-src 'self'/,
  "x-frame-options": /^DENY$/,
  "x-content-type-options": /^nosniff$/,
  "referrer-policy": /^strict-origin-when-cross-origin$/,
  "permissions-policy": /camera=\(\)/,
  "strict-transport-security": /max-age=\d+/,
};

const PATHS = ["/login", "/dashboard", "/explorer", "/chat"];

test.describe("Security headers (CSP + a friends)", () => {
  for (const path of PATHS) {
    test(`${path} envía todos los security headers`, async ({ page }) => {
      const response = await page.goto(path);
      expect(response).not.toBeNull();
      const headers = response!.headers();
      for (const [name, pattern] of Object.entries(REQUIRED_HEADERS)) {
        const value = headers[name];
        expect(value, `falta header ${name} en ${path}`).toBeDefined();
        expect(value!, `header ${name} no matchea esperado en ${path}`).toMatch(pattern);
      }
    });
  }

  test("X-Powered-By NO está presente (poweredByHeader: false)", async ({
    page,
  }) => {
    const response = await page.goto("/login");
    expect(response!.headers()["x-powered-by"]).toBeUndefined();
  });

  test("CSP incluye las directivas críticas", async ({ page }) => {
    const response = await page.goto("/login");
    const csp = response!.headers()["content-security-policy"]!;
    expect(csp).toContain("frame-ancestors 'none'");
    expect(csp).toContain("base-uri 'self'");
    expect(csp).toContain("form-action 'self'");
    expect(csp).toContain("upgrade-insecure-requests");
    expect(csp).toContain("object-src");
    expect(csp).toMatch(/object-src 'none'|default-src 'self'/);
  });
});
