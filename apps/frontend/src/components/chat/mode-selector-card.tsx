"use client";

import { Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { cn } from "@/lib/utils";
import type { ModeCopy } from "@/lib/chat/mode-copy";

interface ModeSelectorCardProps {
  copy: ModeCopy;
  selected: boolean;
  pending: boolean;
  onStart: () => void;
}

/**
 * Card de selección de modo del agente.
 * Presentational: no decide qué pasa al iniciar — el padre (chat/page.tsx)
 * crea la sesión y navega. Esto deja el componente reutilizable desde el
 * empty state del dashboard u otras superficies.
 */
export function ModeSelectorCard({
  copy,
  selected,
  pending,
  onStart,
}: ModeSelectorCardProps) {
  const Icon = copy.icon;
  return (
    <Card
      className={cn(
        "flex h-full flex-col transition-shadow",
        selected
          ? "border-sqa-naranja shadow-md ring-1 ring-sqa-naranja/40"
          : "hover:shadow-md",
      )}
      aria-current={selected || undefined}
    >
      <CardHeader>
        <div className="mb-3 flex items-center justify-between">
          <span
            className={cn(
              "hex-clip-flat flex h-12 w-12 items-center justify-center",
              selected ? "bg-sqa-naranja" : "bg-muted",
            )}
            aria-hidden
          >
            <Icon
              className={cn(
                "h-5 w-5",
                selected ? "text-sqa-ink" : "text-muted-foreground",
              )}
            />
          </span>
          <span
            className={cn(
              "rounded-full px-2 py-0.5 font-display text-[11px] font-extrabold tracking-[0.06em]",
              // Fondo sólido + texto oscuro (~ink) garantiza WCAG AA con
              // el naranja SQA (el variant con tint /15 + text-naranja no
              // alcanza el contraste mínimo de 4.5:1).
              selected
                ? "bg-sqa-naranja text-sqa-ink"
                : "bg-muted text-muted-foreground",
            )}
            aria-label={`Modo ${copy.letter}`}
          >
            Modo {copy.letter}
          </span>
        </div>
        <CardTitle>{copy.title}</CardTitle>
        <CardDescription>{copy.short}</CardDescription>
      </CardHeader>
      <CardContent className="flex-1">
        <p className="text-sm text-muted-foreground">{copy.description}</p>
      </CardContent>
      <CardFooter>
        <Button
          variant={selected ? "accent" : "outline"}
          className="w-full"
          onClick={onStart}
          disabled={pending}
        >
          {pending && selected ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              Creando sesión...
            </>
          ) : (
            copy.cta
          )}
        </Button>
      </CardFooter>
    </Card>
  );
}
