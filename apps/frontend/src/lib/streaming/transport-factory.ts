/**
 * Factory del transport por defecto.
 *
 * Único punto del código donde se elige la implementación concreta del
 * `MessageTransport`. La UI siempre consume `getDefaultTransport()` — el día
 * que llegue el backend SSE real (Fase 2) se sustituye el `new MockMessageTransport()`
 * por `new SseMessageTransport(apiClient)` sin tocar nada más (DIP).
 *
 * Singleton: el mock es stateless entre llamadas a `sendMessage` (cada call
 * crea su propio generator), por lo que cachear la instancia es seguro y
 * evita re-creaciones innecesarias en cada render del page.
 */
import { MockMessageTransport } from "@/lib/streaming/mock-transport";
import type { MessageTransport } from "@/lib/streaming/transport";

let cached: MessageTransport | null = null;

export function getDefaultTransport(): MessageTransport {
  if (!cached) {
    cached = new MockMessageTransport();
  }
  return cached;
}
