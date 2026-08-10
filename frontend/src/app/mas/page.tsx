"use client";

import Link from "next/link";
import AuthGuard from "@/components/AuthGuard";
import { useAuth } from "@/lib/auth";

const LINKS = [
  { href: "/alertas", label: "Alertas" },
  { href: "/deudores", label: "Deudores" },
  { href: "/categorias", label: "Categorías" },
];

function MasContent() {
  const { logout } = useAuth();

  return (
    <main className="mx-auto max-w-lg px-4 pb-24 pt-6">
      <h1 className="mb-6 text-xl font-semibold">Más</h1>

      <ul className="mb-6 divide-y divide-neutral-100 overflow-hidden rounded-xl border border-neutral-200 dark:divide-neutral-800 dark:border-neutral-800">
        {LINKS.map((link) => (
          <li key={link.href}>
            <Link href={link.href} className="flex items-center justify-between px-4 py-3 text-sm font-medium">
              {link.label}
              <span className="text-neutral-400">›</span>
            </Link>
          </li>
        ))}
      </ul>

      <button
        onClick={logout}
        className="w-full rounded-xl border border-neutral-200 px-4 py-3 text-sm font-medium text-red-600 dark:border-neutral-800"
      >
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
