"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { Compass, UserPen, UsersRound } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { SqaLogo } from "@/components/brand/sqa-logo";
import { AriaMascot } from "@/components/brand/aria-mascot";
import { useAuth } from "@/lib/auth/auth-provider";
import { ROLES } from "@/lib/mocks/data";
import type { RoleId } from "@/types/domain";

const ROLE_ICONS: Record<RoleId, React.ComponentType<{ className?: string }>> = {
  capturador: UserPen,
  owner: UsersRound,
  gklead: Compass,
};

export default function LoginPage() {
  const { user, signIn, isLoading } = useAuth();
  const router = useRouter();
  const t = useTranslations("login");
  const tRoles = useTranslations("roles");

  React.useEffect(() => {
    if (!isLoading && user) router.replace("/dashboard");
  }, [user, isLoading, router]);

  return (
    <main
      className="grid min-h-screen place-items-center px-6 py-12"
      style={{
        background:
          "radial-gradient(ellipse 800px 500px at 80% 10%, hsl(var(--sqa-azul-medio) / 0.45), transparent 60%), radial-gradient(ellipse 500px 400px at 10% 90%, hsl(var(--sqa-naranja) / 0.18), transparent 60%), hsl(var(--sqa-ink))",
      }}
    >
      <div className="grid w-full max-w-5xl gap-12 lg:grid-cols-[1fr_460px] lg:items-center">
        <section className="text-white">
          <SqaLogo mode="light" className="h-8 mb-10" />
          <h1 className="font-display text-4xl font-black tracking-[-0.025em] sm:text-5xl">
            Knowledge Base
          </h1>
          <p className="mt-4 max-w-md text-base text-white/80">
            La base de conocimiento del equipo SQA — capturada, consultada y
            curada con Aria.
          </p>
          <div className="mt-8 flex items-center gap-4">
            <AriaMascot size={56} status="speaking" />
            <div>
              <div className="eyebrow text-white/60">Tu agente</div>
              <div className="font-display text-lg font-bold">Aria</div>
            </div>
          </div>
        </section>

        <Card className="border-white/10 bg-card/95 p-8 backdrop-blur">
          <div className="eyebrow mb-2">Modo demo · auth stub</div>
          <h2 className="font-display text-xl font-bold">
            Entrá con un rol de prueba
          </h2>
          <p className="mt-1 text-sm text-muted-foreground">
            En producción esta pantalla redirige a Microsoft Entra ID. En esta
            etapa, elegí el rol con el que querés probar la app.
          </p>

          <div className="mt-6 grid gap-2.5">
            {(Object.keys(ROLES) as RoleId[]).map((id) => {
              const role = ROLES[id];
              const Icon = ROLE_ICONS[id];
              return (
                <button
                  key={id}
                  onClick={() => signIn(id)}
                  className="group flex items-center gap-3.5 rounded-md border border-border bg-card px-4 py-3 text-left transition-colors hover:border-sqa-naranja/40 hover:bg-sqa-naranja/[0.04] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                  aria-label={t("loginAs", {
                    label: tRoles(`${id}.label`),
                    name: role.name,
                  })}
                >
                  <span className="hex-clip-flat flex h-9 w-9 shrink-0 items-center justify-center bg-sqa-azul-corp text-sqa-naranja">
                    <Icon className="h-4 w-4" />
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="block text-sm font-bold text-foreground">
                      {role.name}
                    </span>
                    <span className="block text-xs text-muted-foreground">
                      {role.label} · {role.sub}
                    </span>
                  </span>
                  <span className="text-xs font-mono text-muted-foreground transition-colors group-hover:text-foreground">
                    {role.email}
                  </span>
                </button>
              );
            })}
          </div>

          <div className="mt-6 flex items-center gap-3 rounded-md border border-dashed border-border bg-muted/40 px-3 py-2 text-xs text-muted-foreground">
            <Button variant="ghost" size="sm" disabled className="-ml-2">
              Entrar con Microsoft
            </Button>
            <span>Disponible al integrar Entra ID (Fase 11).</span>
          </div>
        </Card>
      </div>
    </main>
  );
}
