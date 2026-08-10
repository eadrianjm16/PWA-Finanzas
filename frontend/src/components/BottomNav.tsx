"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/lib/auth";

const TABS = [
  { href: "/accounts", label: "Saldo" },
  { href: "/movimientos", label: "Mov." },
  { href: "/analisis", label: "Análisis" },
  { href: "/presupuestos", label: "Presup." },
  { href: "/mas", label: "Más" },
];

export default function BottomNav() {
  const pathname = usePathname();
  const { isAuthenticated } = useAuth();

  if (pathname === "/login" || !isAuthenticated) return null;

  return (
    <nav
      className="fixed inset-x-0 bottom-0 z-10 border-t border-neutral-200 bg-white/95 backdrop-blur dark:border-neutral-800 dark:bg-neutral-950/95"
      style={{ paddingBottom: "env(safe-area-inset-bottom)" }}
    >
      <div className="mx-auto flex max-w-lg items-center">
        {TABS.map((tab) => {
          const active = pathname.startsWith(tab.href);
          return (
            <Link
              key={tab.href}
              href={tab.href}
              className={`flex-1 py-3 text-center text-xs font-medium ${
                active ? "text-neutral-900 dark:text-white" : "text-neutral-400"
              }`}
            >
              {tab.label}
            </Link>
          );
        })}
      </div>
    </nav>
  );
}
