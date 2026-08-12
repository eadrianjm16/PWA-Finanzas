"use client";

import Link from "next/link";
import useSWR from "swr";
import {
  Bell,
  CalendarClock,
  ChevronRight,
  CreditCard,
  Lock,
  LogOut,
  Repeat,
  ShieldCheck,
  Tags,
  Target,
  Users,
} from "lucide-react";
import AuthGuard from "@/components/AuthGuard";
import { apiFetch } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { Me } from "@/lib/types";

const LINKS = [
  { href: "/alertas", label: "Alertas", icon: Bell },
  { href: "/suscripciones", label: "Suscripciones", icon: Repeat },
  { href: "/gastos-fijos", label: "Gasto Fijo", icon: CalendarClock },
  { href: "/metas", label: "Metas de ahorro", icon: Target },
  { href: "/prestamos", label: "Préstamos", icon: CreditCard },
  { href: "/deudores", label: "Deudores", icon: Users },
  { href: "/categorias", label: "Categorías", icon: Tags },
  { href: "/bloqueo", label: "Bloqueo con PIN", icon: Lock },
];

function MasContent() {
  const { logout } = useAuth();
  const { data: me } = useSWR<Me>("/api/auth/me", apiFetch);

  const links = me?.is_admin ? [...LINKS, { href: "/admin", label: "Gestión de cuentas", icon: ShieldCheck }] : LINKS;

  return (
    <main className="mx-auto max-w-lg px-4 pb-28 pt-6">
      <h1 className="mb-6 text-2xl font-semibold tracking-tight">Más</h1>

      <ul className="mb-6 overflow-hidden rounded-2xl border border-surface-border bg-surface shadow-[var(--shadow-card)]">
        {links.map((link, index) => {
          const Icon = link.icon;
          return (
            <li key={link.href} className={index > 0 ? "border-t border-surface-border" : ""}>
              <Link
                href={link.href}
                className="flex items-center gap-3 px-4 py-3.5 text-sm font-medium transition hover:bg-surface-hover"
              >
                <span className="flex h-9 w-9 items-center justify-center rounded-full bg-surface-hover">
                  <Icon className="h-4 w-4 text-muted" />
                </span>
                <span className="flex-1">{link.label}</span>
                <ChevronRight className="h-4 w-4 text-muted-soft" />
              </Link>
            </li>
          );
        })}
      </ul>

      <button
        onClick={logout}
        className="flex w-full items-center justify-center gap-2 rounded-2xl border border-danger/20 bg-danger-soft px-4 py-3.5 text-sm font-medium text-danger"
      >
        <LogOut className="h-4 w-4" />
        Salir
      </button>
    </main>
  );
}

export default function MasPage() {
  return (
    <AuthGuard>
      <MasContent />
    </AuthGuard>
  );
}
