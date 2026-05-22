/**
 * Server actions para cambiar el locale activo.
 *
 * El locale vive en una cookie `NEXT_LOCALE`. Cuando el usuario cambia
 * idioma desde el switcher, esta action lo persiste y triggea revalidación
 * del path actual para que el bundle nuevo se aplique.
 */
"use server";

import { cookies } from "next/headers";
import { revalidatePath } from "next/cache";
import {
  isLocale,
  LOCALE_COOKIE,
  LOCALE_COOKIE_MAX_AGE,
  type Locale,
} from "./config";

export async function setLocale(locale: Locale): Promise<void> {
  if (!isLocale(locale)) {
    throw new Error(`Locale no soportado: ${locale}`);
  }
  const cookieStore = await cookies();
  cookieStore.set({
    name: LOCALE_COOKIE,
    value: locale,
    httpOnly: false,
    sameSite: "lax",
    maxAge: LOCALE_COOKIE_MAX_AGE,
    path: "/",
  });
  // Revalidar la raíz fuerza a Next a re-renderizar con el nuevo locale.
  revalidatePath("/", "layout");
}
