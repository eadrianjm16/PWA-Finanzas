"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { LayoutGrid, ListOrdered, MoreHorizontal, PieChart, Wallet } from "lucide-react";
import { useAuth } from "@/lib/auth";

const TABS = [
  { href: "/accounts", label: "Saldo", icon: Wallet },
  { href: "/movimientos", label: "Movs.", icon: ListOrdered },
  { href: "/analisis", label: "Análisis", icon: PieChart },
  { href: "/presupuestos", label: "Presup.", icon: LayoutGrid },
  { href: "/mas", label: "Más", icon: MoreHorizontal },
];

export default function BottomNav() {
  const pathname = usePathname();
  const { isAuthenticated } = useAuth();

  if (pathname === "/login" || !isAuthenticated) return null;

  return (
    <nav
      className="fixed inset-x-0 bottom-0 z-10 border-t border-surface-border bg-surface/85 backdrop-blur-xl"
      style={{ paddingBottom: "env(safe-area-inset-bottom)" }}
    >
      <div className="mx-auto flex max-w-lg items-stretch px-1">
        {TABS.map((tab) => {
          const active = pathname.startsWith(tab.href);
          const Icon = tab.icon;
          return (
            <Link
              key={tab.href}
              href={tab.href}
              className="group relative flex flex-1 flex-col items-center gap-1 py-2.5 text-center"
            >
              <span
                className={`flex h-8 w-12 items-center justify-center rounded-full transition-colors ${
                  active ? "bg-brand-soft" : "group-active:bg-surface-hover"
                }`}
              >
                <Icon
                  className={`h-5 w-5 transition-colors ${active ? "text-brand" : "text-muted-soft"}`}
                  strokeWidth={active ? 2.25 : 1.75}
                />
              </span>
              <span className={`text-[11px] font-medium transition-colors ${active ? "text-foreground" : "text-muted-soft"}`}>
                {tab.label}
              </span>
            </Link>
          );
        })}
      </div>
    </nav>
  );
}
