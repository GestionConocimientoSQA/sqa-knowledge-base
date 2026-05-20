"use client";

import { useEffect, useState } from "react";

/**
 * Devuelve una versión "estabilizada" de `value` que solo se actualiza
 * después de `delayMs` sin nuevos cambios. Útil para search inputs:
 * el componente lee `value` (sincronizado con el textbox) pero la query
 * a la API se hace con el resultado de este hook.
 *
 * Cancela el timer pendiente al desmontar y en cada cambio de input,
 * por lo que no dispara updates sobre componentes desmontados.
 */
export function useDebouncedValue<T>(value: T, delayMs: number): T {
  const [debounced, setDebounced] = useState(value);

  useEffect(() => {
    const handle = setTimeout(() => setDebounced(value), delayMs);
    return () => clearTimeout(handle);
  }, [value, delayMs]);

  return debounced;
}
