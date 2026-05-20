"use client";

import { useEffect, useRef, useState } from "react";
import { Search, X } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { useDebouncedValue } from "@/lib/hooks/use-debounced-value";
import { cn } from "@/lib/utils";

interface SearchInputProps {
  /** Valor "fuente de verdad" (típicamente desde URL state). */
  value: string;
  /** Disparado cuando el valor escrito se estabiliza (debounce). */
  onDebouncedChange: (value: string) => void;
  placeholder?: string;
  debounceMs?: number;
  /** ID del input para asociar el label externamente. */
  id?: string;
  className?: string;
}

const DEFAULT_DEBOUNCE_MS = 300;

/**
 * Search input controlado por valor inmediato (sin lag de tecleo), que
 * notifica al padre solo cuando el valor se estabilizó por `debounceMs`.
 *
 * Permite que el padre escriba programáticamente (ej: lectura de URL al
 * montar, reset) sincronizando el input con `value` cuando este cambia
 * fuera del foco del usuario.
 */
export function SearchInput({
  value,
  onDebouncedChange,
  placeholder = "Buscar…",
  debounceMs = DEFAULT_DEBOUNCE_MS,
  id,
  className,
}: SearchInputProps) {
  const [local, setLocal] = useState(value);
  const debounced = useDebouncedValue(local, debounceMs);
  // Refs para evitar disparar `onDebouncedChange` cuando el cambio vino
  // del padre (sincronización descendente), solo cuando vino del usuario.
  const lastEmittedRef = useRef(value);

  // Sincronización descendente: si el padre cambia `value` (reset, URL
  // change externo), el input refleja el nuevo valor.
  useEffect(() => {
    if (value !== local) {
      setLocal(value);
      lastEmittedRef.current = value;
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [value]);

  // Emisión ascendente: cuando el debounced cambia respecto al último
  // valor emitido, notificamos al padre.
  useEffect(() => {
    if (debounced !== lastEmittedRef.current) {
      lastEmittedRef.current = debounced;
      onDebouncedChange(debounced);
    }
  }, [debounced, onDebouncedChange]);

  const showClear = local.length > 0;

  return (
    <div className={cn("relative flex items-center", className)}>
      <Search
        className="pointer-events-none absolute left-3 h-4 w-4 text-muted-foreground"
        aria-hidden
      />
      <Input
        id={id}
        type="search"
        value={local}
        onChange={(e) => setLocal(e.target.value)}
        placeholder={placeholder}
        aria-label="Buscar documentos"
        className="pl-9 pr-9"
      />
      {showClear && (
        <Button
          type="button"
          variant="ghost"
          size="icon"
          className="absolute right-1 h-7 w-7 text-muted-foreground hover:text-foreground"
          onClick={() => setLocal("")}
          aria-label="Limpiar búsqueda"
        >
          <X className="h-3.5 w-3.5" />
        </Button>
      )}
    </div>
  );
}
