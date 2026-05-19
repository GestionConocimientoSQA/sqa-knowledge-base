"use client";

import * as React from "react";
import { Sidebar } from "@/components/layout/sidebar";
import { Topbar } from "@/components/layout/topbar";
import { Skeleton } from "@/components/ui/skeleton";
import { useRequireAuth } from "@/lib/auth/auth-provider";
import { usePathname } from "next/navigation";

interface RouteMeta {
  title: string;
  breadcrumb?: string;
}

const ROUTE_META: ReadonlyArray<{ match: RegExp; meta: RouteMeta }> = [
  { match: /^\/dashboard/, meta: { title: "Métricas", breadcrumb: "Trabajo" } },
  {
    match: /^\/chat\/[^/]+$/,
    meta: { title: "Conversación con Aria", breadcrumb: "Trabajo" },
  },
  {
    match: /^\/chat$/,
    meta: { title: "Iniciar conversación", breadcrumb: "Trabajo" },
  },
  {
    match: /^\/ingestion/,
    meta: { title: "Cola de ingesta", breadcrumb: "Trabajo" },
  },
  {
    match: /^\/explorer/,
    meta: { title: "Catálogo", breadcrumb: "Conocimiento" },
  },
  {
    match: /^\/admin/,
    meta: { title: "Taxonomía y gobierno", breadcrumb: "Gobierno" },
  },
];

function resolveMeta(pathname: string): RouteMeta {
  return (
    ROUTE_META.find((r) => r.match.test(pathname))?.meta ?? { title: "SQA KB" }
  );
}

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const { user, isLoading } = useRequireAuth();
  const pathname = usePathname();

  if (isLoading || !user) {
    return (
      <div className="flex h-screen items-center justify-center">
        <Skeleton className="h-10 w-32" />
      </div>
    );
  }

  const meta = resolveMeta(pathname);

  return (
    <div className="flex h-screen overflow-hidden bg-background">
      <Sidebar />
      <div className="flex min-w-0 flex-1 flex-col">
        <Topbar title={meta.title} breadcrumb={meta.breadcrumb} />
        <main className="flex-1 overflow-auto" role="main">
          {children}
        </main>
      </div>
    </div>
  );
}
