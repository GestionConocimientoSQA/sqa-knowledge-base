"use client";

import * as React from "react";
import Link from "next/link";
import { usePathname, useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";
import {
  LayoutDashboard,
  Mic,
  SearchCode,
  Inbox,
  LibraryBig,
  BookUser,
  Settings2,
  Settings,
  type LucideIcon,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { SqaLogo } from "@/components/brand/sqa-logo";
import { AriaMascot } from "@/components/brand/aria-mascot";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { SidebarSessions } from "@/components/layout/sidebar-sessions";
import { useAuth } from "@/lib/auth/auth-provider";
import { useUiStore } from "@/stores/ui-store";
import { ROLES } from "@/lib/mocks/data";

interface NavItem {
  id: string;
  /** Clave i18n bajo el namespace `nav`. */
  labelKey: string;
  icon: LucideIcon;
  href: string;
  count?: number;
  /**
   * Permite que dos items con el mismo `href` se diferencien por query string
   * (ej. /chat?mode=captura vs /chat?mode=consulta). Si se omite, el activeMatch
   * cae a `pathname.startsWith(href)`.
   */
  activeWhen?: (pathname: string, search: URLSearchParams) => boolean;
}

interface NavGroup {
  /** Clave i18n bajo el namespace `nav`. */
  labelKey: string;
  items: NavItem[];
}

const NAV_GROUPS: NavGroup[] = [
  {
    labelKey: "groupWork",
    items: [
      { id: "dashboard", labelKey: "dashboard", icon: LayoutDashboard, href: "/dashboard" },
      {
        id: "chat-capture",
        labelKey: "captura",
        icon: Mic,
        href: "/chat?mode=captura",
        activeWhen: (p, s) => p === "/chat" && s.get("mode") === "captura",
      },
      {
        id: "chat-consulta",
        labelKey: "consulta",
        icon: SearchCode,
        href: "/chat?mode=consulta",
        activeWhen: (p, s) => p === "/chat" && s.get("mode") === "consulta",
      },
      { id: "ingestion", labelKey: "ingestion", icon: Inbox, href: "/ingestion", count: 4 },
    ],
  },
  {
    labelKey: "groupKnowledge",
    items: [
      { id: "explorer", labelKey: "explorer", icon: LibraryBig, href: "/explorer" },
      { id: "my-captures", labelKey: "myCaptures", icon: BookUser, href: "/my-captures" },
    ],
  },
  {
    labelKey: "groupGovernance",
    items: [{ id: "admin", labelKey: "admin", icon: Settings2, href: "/admin" }],
  },
];

export function Sidebar() {
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const { user } = useAuth();
  const collapsed = useUiStore((s) => s.sidebarCollapsed);
  const role = user ? ROLES[user.roleId] : null;
  const tNav = useTranslations("nav");

  return (
    <aside
      className={cn(
        "relative flex h-screen flex-col overflow-hidden border-r border-white/[0.06] text-white transition-[width] duration-300 ease-out",
        collapsed ? "w-[64px]" : "w-[248px]",
      )}
      style={{
        background:
          "linear-gradient(180deg, hsl(var(--sqa-ink)) 0%, hsl(var(--sqa-azul-corp)) 100%)",
      }}
    >
      {/* Decorative glow */}
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 opacity-[0.06]"
        style={{
          background: `
            radial-gradient(circle at 90% 0%, hsl(var(--sqa-naranja)) 0%, transparent 30%),
            radial-gradient(circle at 0% 100%, hsl(var(--sqa-azul-medio-claro)) 0%, transparent 40%)
          `,
        }}
      />

      {/* Brand */}
      <div
        className={cn(
          "relative z-10 flex items-center gap-2.5",
          collapsed ? "justify-center py-4" : "justify-between px-5 py-[18px]",
        )}
      >
        {collapsed ? (
          <div className="hex-clip-flat flex h-8 w-8 items-center justify-center bg-sqa-naranja">
            <span className="font-display text-xs font-black text-sqa-ink">
              GK
            </span>
          </div>
        ) : (
          <div className="flex items-center gap-2.5">
            <SqaLogo mode="light" className="h-[26px]" />
            <span className="rounded-full bg-sqa-naranja/15 px-1.5 py-0.5 font-display text-[11px] font-extrabold tracking-[0.06em] text-sqa-naranja">
              GK
            </span>
          </div>
        )}
      </div>

      {/* Mascot card */}
      {!collapsed && (
        <div className="relative z-10 mx-3.5 mb-4 flex items-center gap-3 rounded-[14px] border border-white/[0.07] bg-white/[0.04] p-3.5">
          <AriaMascot size={44} status="speaking" />
          <div className="min-w-0 flex-1">
            <div className="font-display text-[11px] font-bold uppercase tracking-[0.06em] text-white/60">
              {tNav("activeAgent")}
            </div>
            <div className="text-[13px] font-bold text-white">Aria</div>
          </div>
        </div>
      )}

      {/* Nav */}
      <nav className="relative z-10 flex-1 overflow-y-auto px-2 pb-4">
        {!collapsed && <SidebarSessions />}
        {NAV_GROUPS.map((group) => (
          <div key={group.labelKey} className="mb-[18px]">
            {!collapsed && (
              <div className="px-3 pb-2 pt-1 font-display text-[9.5px] font-extrabold uppercase tracking-[0.14em] text-white/60">
                {tNav(group.labelKey)}
              </div>
            )}
            {group.items.map((item) => {
              const active = item.activeWhen
                ? item.activeWhen(pathname, searchParams)
                : pathname.startsWith(item.href);
              const Icon = item.icon;
              const label = tNav(item.labelKey);
              return (
                <Link
                  key={item.id}
                  href={item.href as never}
                  title={collapsed ? label : undefined}
                  className={cn(
                    "relative my-0.5 flex items-center gap-3 rounded-[10px] font-display text-[13px] font-semibold transition-colors",
                    collapsed
                      ? "justify-center py-2.5"
                      : "px-3 py-[9px]",
                    active
                      ? "bg-sqa-naranja/[0.12] text-white"
                      : "text-white/60 hover:bg-white/[0.05] hover:text-white",
                  )}
                >
                  {active && (
                    <span className="absolute -left-2 top-2 bottom-2 w-[3px] rounded-full bg-sqa-naranja" />
                  )}
                  <Icon className="h-[17px] w-[17px]" />
                  {!collapsed && (
                    <>
                      <span className="flex-1 truncate">{label}</span>
                      {item.count !== undefined && (
                        <span className="rounded-full bg-sqa-naranja px-1.5 py-[1px] text-[10px] font-black text-sqa-ink">
                          {item.count}
                        </span>
                      )}
                    </>
                  )}
                </Link>
              );
            })}
          </div>
        ))}
      </nav>

      {/* User footer */}
      {!collapsed && role && (
        <div className="relative z-10 m-3.5 flex items-center gap-2.5 rounded-xl border border-white/[0.06] bg-white/[0.03] p-3">
          <Avatar className="h-8 w-8">
            <AvatarFallback className="text-xs">
              {role.name
                .split(" ")
                .map((p) => p[0])
                .slice(0, 2)
                .join("")}
            </AvatarFallback>
          </Avatar>
          <div className="min-w-0 flex-1">
            <div className="truncate text-[13px] font-bold text-white">
              {role.name}
            </div>
            <div className="text-[11px] text-white/60">{role.label}</div>
          </div>
          <Settings className="h-[15px] w-[15px] text-white/60" />
        </div>
      )}
    </aside>
  );
}
