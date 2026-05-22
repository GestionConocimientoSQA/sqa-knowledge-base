/**
 * Configuración de i18n (next-intl).
 *
 * Estrategia: cookie-based locale (sin prefijos en URL). El locale activo
 * vive en la cookie `NEXT_LOCALE`. Default: `es-CO`. Los locales soportados
 * son una lista cerrada — cualquier valor fuera se trata como inválido.
 */

export const LOCALES = ["es-CO", "en-US"] as const;

export type Locale = (typeof LOCALES)[number];

export const DEFAULT_LOCALE: Locale = "es-CO";

export const LOCALE_COOKIE = "NEXT_LOCALE";

/**
 * Cuánto vive la cookie del locale. 1 año — suficiente para que el usuario
 * no tenga que re-elegir constantemente sin volverse "permanente".
 */
export const LOCALE_COOKIE_MAX_AGE = 60 * 60 * 24 * 365;

export function isLocale(value: unknown): value is Locale {
  return typeof value === "string" && (LOCALES as readonly string[]).includes(value);
}

/**
 * Nombre legible del locale para mostrar en el switcher.
 */
export const LOCALE_LABELS: Record<Locale, string> = {
  "es-CO": "Español (Colombia)",
  "en-US": "English (US)",
};
