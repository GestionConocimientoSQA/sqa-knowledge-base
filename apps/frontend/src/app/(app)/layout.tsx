"use client";

import * as React from "react";
import { useTranslations } from "next-intl";
import { Sidebar } from "@/components/layout/sidebar";
import { Topbar } from "@/components/layout/topbar";
import { Skeleton } from "@/components/ui/skeleton";
import { useRequireAuth } from "@/lib/auth/auth-provider";
import { usePathname } from "next/navigation";

interface RouteMeta {
  titleKey: string;
  breadcrumbKey?: string;
}

const ROUTE_META: ReadonlyArray<{ match: RegExp; meta: RouteMeta }> = [
  { match: /^\/dashboard/, meta: { titleKey: "dashboard", breadcrumbKey: "groupWork" } },
  {
    match: /^\/chat\/[^/]+$/,
    meta: { titleKey: "chat", breadcrumbKey: "groupWork" },
  },
  {
    match: /^\/chat$/,
    meta: { titleKey: "chatStart", breadcrumbKey: "groupWork" },
  },
  {
    match: /^\/ingestion/,
    meta: { titleKey: "ingestion", breadcrumbKey: "groupWork" },
  },
  {
    match: /^\/explorer/,
    meta: { titleKey: "explorer", breadcrumbKey: "groupKnowledge" },
  },
  {
    match: /^\/admin/,
    meta: { titleKey: "admin", breadcrumbKey: "groupGovernance" },
  },
];

function resolveMeta(pathname: string): RouteMeta {
  return (
    ROUTE_META.find((r) => r.match.test(pathname))?.meta ?? { titleKey: "" }
  );
}

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const { user, isLoading } = useRequireAuth();
  const pathname = usePathname();
  const tTopbar = useTranslations("topbar.title");
  const tNav = useTranslations("nav");
  const tCommon = useTranslations("common");

  if (isLoading || !user) {
    return (
      <div className="flex h-screen items-center justify-center">
        <Skeleton className="h-10 w-32" />
      </div>
    );
  }

  const meta = resolveMeta(pathname);
  const title = meta.titleKey ? tTopbar(meta.titleKey) : tCommon("appName");
  const breadcrumb = meta.breadcrumbKey ? tNav(meta.breadcrumbKey) : undefined;

  return (
    <div className="flex h-screen overflow-hidden bg-background">
      {/*
       * Skip-link al contenido principal. Visualmente oculto hasta que recibe
       * focus por teclado (primer Tab desde la página). Permite saltar la
       * navegación lateral, requerimiento de WCAG 2.4.1.
       */}
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-50 focus:rounded-md focus:bg-sqa-naranja focus:px-4 focus:py-2 focus:font-display focus:font-bold focus:text-sqa-ink focus:shadow-lg focus:outline-none focus:ring-2 focus:ring-sqa-naranja focus:ring-offset-2"
      >
        {tCommon("skipToContent")}
      </a>
      <Sidebar />
      <div className="flex min-w-0 flex-1 flex-col">
        <Topbar title={title} breadcrumb={breadcrumb} />
        <main
          id="main-content"
          className="flex-1 overflow-auto focus-visible:outline-none"
          role="main"
          tabIndex={-1}
        >
          {children}
        </main>
      </div>
    </div>
  );
}
