import ky from "ky";

const API_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

/**
 * Cliente HTTP base. En modo stub (Fase 5) las llamadas pueden caer al backend
 * mock o resolverse directamente desde lib/api/*-mock.ts.
 *
 * Cuando Fase 6 introduzca SSE para chat, se usará fetch nativo con
 * EventSource-polyfill compatible con headers de auth.
 */
export const api = ky.create({
  prefixUrl: API_URL,
  timeout: 30_000,
  retry: { limit: 2, methods: ["get"] },
  hooks: {
    beforeRequest: [
      (request) => {
        // En auth real (MSAL) acá inyectaríamos `Authorization: Bearer ...`.
        // En stub: header explícito para que el backend lo trate como auth bypass.
        request.headers.set("X-Stub-Auth", "1");
        request.headers.set("X-Request-ID", crypto.randomUUID());
      },
    ],
  },
});
