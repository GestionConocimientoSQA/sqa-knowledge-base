"use client";

import { useTransition } from "react";
import { useLocale, useTranslations } from "next-intl";
import { Languages } from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Button } from "@/components/ui/button";
import { setLocale } from "@/i18n/actions";
import { LOCALES, LOCALE_LABELS, type Locale } from "@/i18n/config";

/**
 * Switcher de idioma para el topbar. Persiste el locale en cookie y
 * recarga el árbol del layout via `revalidatePath` para que el bundle
 * de mensajes nuevo se aplique.
 */
export function LanguageSwitcher() {
  const t = useTranslations("common");
  const current = useLocale();
  const [pending, startTransition] = useTransition();

  const handleSelect = (next: Locale) => {
    if (next === current) return;
    startTransition(async () => {
      await setLocale(next);
    });
  };

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          variant="ghost"
          size="icon"
          aria-label={t("language")}
          disabled={pending}
        >
          <Languages className="h-4 w-4" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="min-w-[180px]">
        <DropdownMenuLabel>{t("language")}</DropdownMenuLabel>
        <DropdownMenuSeparator />
        {LOCALES.map((locale) => (
          <DropdownMenuItem
            key={locale}
            onClick={() => handleSelect(locale)}
            className={current === locale ? "font-bold text-sqa-naranja" : ""}
          >
            {LOCALE_LABELS[locale]}
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
