import createNextIntlPlugin from "next-intl/plugin";

const withNextIntl = createNextIntlPlugin("./src/i18n/request.ts");

/** @type {import('next').NextConfig} */

const isDev = process.env.NODE_ENV !== "production";

/**
 * Content-Security-Policy.
 *
 * En dev el bundler usa `eval` y mucho `inline` para React Refresh y HMR;
 * la CSP queda más permisiva. En producción se cierran scripts inline
 * (Next inyecta sus chunks con archivos servidos por `self`).
 *
 * Pendiente para Fase 10 completa: nonce dinámico vía middleware para
 * eliminar `unsafe-inline` también en scripts inline de hidratación.
 */
const cspDirectives = [
  `default-src 'self'`,
  // Scripts: en prod permitimos solo self + (Next emite algunos inline durante
  // la primera hidratación). 'strict-dynamic' habilita chunks dinámicos.
  isDev
    ? `script-src 'self' 'unsafe-eval' 'unsafe-inline'`
    : `script-src 'self' 'unsafe-inline'`,
  // Tailwind/shadcn inyectan estilos inline; 'unsafe-inline' es inevitable
  // hasta cambiar a runtime con CSS Modules o nonces. Aceptable: no permite
  // ejecución, solo declaraciones.
  `style-src 'self' 'unsafe-inline'`,
  // Imágenes: self + data: para SVGs en components + blob: para previews
  // de uploads (Fase 6.6).
  `img-src 'self' data: blob:`,
  // next/font self-hosted; data: cubre fonts inlineadas en CSS.
  `font-src 'self' data:`,
  // API: self por ahora; cuando llegue el backend Fase 1, se agrega su URL.
  `connect-src 'self'`,
  // Defensa contra clickjacking — equivalente al X-Frame-Options DENY de abajo.
  `frame-ancestors 'none'`,
  // <base> no puede cambiar el origen — bloquea ataques con base injection.
  `base-uri 'self'`,
  // <form action> solo a self.
  `form-action 'self'`,
  // No permitir <object>, <embed>, <applet> — vectores legacy de XSS.
  `object-src 'none'`,
  // Bloquea mixed content automáticamente.
  `upgrade-insecure-requests`,
].join("; ");

const nextConfig = {
  // standalone se activa solo en CI/Linux para producción Docker.
  // Windows local no puede crear symlinks sin admin, lo cual rompe el copy de traces.
  ...(process.env.NEXT_BUILD_STANDALONE === "true"
    ? { output: "standalone" }
    : {}),
  reactStrictMode: true,
  poweredByHeader: false,
  experimental: {
    typedRoutes: true,
  },
  async headers() {
    return [
      {
        source: "/(.*)",
        headers: [
          { key: "Content-Security-Policy", value: cspDirectives },
          { key: "X-Frame-Options", value: "DENY" },
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
          {
            key: "Permissions-Policy",
            value: "camera=(), microphone=(), geolocation=()",
          },
          {
            key: "Strict-Transport-Security",
            // 2 años, incluye subdominios, preload. Activo en prod (HTTP en dev
            // lo ignora, pero el header se sirve igual — el browser solo lo
            // honra sobre HTTPS).
            value: "max-age=63072000; includeSubDomains; preload",
          },
        ],
      },
    ];
  },
};

export default withNextIntl(nextConfig);
