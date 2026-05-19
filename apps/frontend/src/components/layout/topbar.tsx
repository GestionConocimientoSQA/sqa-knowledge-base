"use client";

import * as React from "react";
import { Menu, LogOut, Sun, Moon, Monitor } from "lucide-react";
import { useTheme } from "next-themes";
import { Button } from "@/components/ui/button";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
} from "@/components/ui/dropdown-menu";
import { AriaMascot } from "@/components/brand/aria-mascot";
import { useAuth } from "@/lib/auth/auth-provider";
import { useUiStore } from "@/stores/ui-store";
import { ROLES } from "@/lib/mocks/data";

interface TopbarProps {
  title: string;
  breadcrumb?: string;
}

export function Topbar({ title, breadcrumb }: TopbarProps) {
  const { user, signOut } = useAuth();
  const toggleSidebar = useUiStore((s) => s.toggleSidebar);
  const { setTheme } = useTheme();
  const role = user ? ROLES[user.roleId] : null;

  return (
    <header
      className="sticky top-0 z-30 flex h-[60px] shrink-0 items-center gap-6 border-b border-border bg-card px-7"
      role="banner"
    >
      <Button
        variant="ghost"
        size="icon"
        onClick={toggleSidebar}
        aria-label="Colapsar o expandir la navegación lateral"
      >
        <Menu className="h-5 w-5" />
      </Button>

      <div className="flex min-w-0 flex-col justify-center">
        {breadcrumb && (
          <div className="eyebrow text-[10px]">{breadcrumb}</div>
        )}
        <h1 className="font-display text-[19px] font-extrabold leading-tight tracking-[-0.01em] text-foreground">
          {title}
        </h1>
      </div>

      <div className="flex-1" />

      {/* Theme toggle */}
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button variant="ghost" size="icon" aria-label="Cambiar tema">
            <Sun className="h-4 w-4 rotate-0 scale-100 transition-all dark:-rotate-90 dark:scale-0" />
            <Moon className="absolute h-4 w-4 rotate-90 scale-0 transition-all dark:rotate-0 dark:scale-100" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end">
          <DropdownMenuItem onClick={() => setTheme("light")}>
            <Sun className="mr-2 h-4 w-4" />
            Claro
          </DropdownMenuItem>
          <DropdownMenuItem onClick={() => setTheme("dark")}>
            <Moon className="mr-2 h-4 w-4" />
            Oscuro
          </DropdownMenuItem>
          <DropdownMenuItem onClick={() => setTheme("system")}>
            <Monitor className="mr-2 h-4 w-4" />
            Sistema
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>

      {/* User identity */}
      {role && (
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <button
              className="flex max-w-[280px] items-center gap-2.5 rounded-full border border-sqa-azul-claro/30 bg-sqa-azul-claro/10 py-1.5 pl-1.5 pr-3.5 font-display transition-colors hover:bg-sqa-azul-claro/15"
              aria-label="Menú de usuario"
            >
              <Avatar className="h-8 w-8">
                <AvatarFallback className="text-xs">
                  {role.name
                    .split(" ")
                    .map((p) => p[0])
                    .slice(0, 2)
                    .join("")}
                </AvatarFallback>
              </Avatar>
              <div className="flex min-w-0 flex-col leading-tight text-left">
                <span className="truncate text-[12.5px] font-bold text-foreground">
                  {role.name}
                </span>
                <span className="truncate font-mono text-[10.5px] text-muted-foreground">
                  {role.email}
                </span>
              </div>
            </button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="min-w-[200px]">
            <DropdownMenuLabel>{role.label}</DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuItem onClick={signOut}>
              <LogOut className="mr-2 h-4 w-4" />
              Cerrar sesión
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      )}

      {/* Agent toggle */}
      <Button variant="outline" size="sm" className="gap-2 rounded-full">
        <AriaMascot size={22} status="idle" />
        Agente
      </Button>
    </header>
  );
}
