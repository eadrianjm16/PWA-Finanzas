"use client";

import Link from "next/link";
import useSWR from "swr";
import { ChevronLeft, Landmark, ListOrdered, ShieldCheck, Trash2, Users } from "lucide-react";
import AuthGuard from "@/components/AuthGuard";
import { SkeletonList } from "@/components/Skeleton";
import { apiFetch, ApiError } from "@/lib/api";
import type { AdminUser, Me } from "@/lib/types";
import { useState } from "react";

function AdminContent() {
  const { data: me } = useSWR<Me>("/api/auth/me", apiFetch);
  const { data: users, mutate } = useSWR<AdminUser[]>(me?.is_admin ? "/api/admin/users" : null, apiFetch);
  const [error, setError] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  async function deleteUser(user: AdminUser) {
    if (
      !window.confirm(
        `¿Borrar la cuenta de ${user.email}? Se eliminarán TODOS sus datos (${user.transactions_count} movimientos, ${user.bank_connections_count} bancos, ${user.debtors_count} deudores). No se puede deshacer.`
      )
    )
      return;
    setDeletingId(user.id);
    setError(null);
    try {
      await apiFetch(`/api/admin/users/${user.id}`, { method: "DELETE" });
      await mutate();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo borrar la cuenta");
    } finally {
      setDeletingId(null);
    }
  }

  if (me && !me.is_admin) {
    return (
      <main className="mx-auto max-w-lg px-4 pb-28 pt-6">
        <Link href="/mas" className="flex items-center gap-1 text-sm font-medium text-muted">
          <ChevronLeft className="h-4 w-4" />
          Más
        </Link>
        <p className="mt-6 text-sm text-muted">No tienes acceso a esta sección.</p>
      </main>
    );
  }

  return (
    <main className="mx-auto max-w-lg px-4 pb-28 pt-6">
      <Link href="/mas" className="flex items-center gap-1 text-sm font-medium text-muted">
        <ChevronLeft className="h-4 w-4" />
        Más
      </Link>

      <div className="mb-6 mt-3 flex items-center gap-2">
        <ShieldCheck className="h-5 w-5 text-brand" />
        <h1 className="text-2xl font-semibold tracking-tight">Gestión de cuentas</h1>
      </div>

      {error && <p className="mb-4 text-sm text-danger">{error}</p>}
      {!users && <SkeletonList rows={3} />}

      <ul className="flex flex-col gap-3">
        {users?.map((user) => (
          <li
            key={user.id}
            className="rounded-2xl border border-surface-border bg-surface p-4 shadow-[var(--shadow-card)]"
          >
            <div className="mb-3 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="text-sm font-medium">{user.email}</span>
                {user.is_admin && (
                  <span className="rounded-full bg-brand-soft px-2 py-0.5 text-[10px] font-semibold text-brand">
                    ADMIN
                  </span>
                )}
              </div>
              {!user.is_admin && (
                <button
                  onClick={() => deleteUser(user)}
                  disabled={deletingId === user.id}
                  className="flex h-8 w-8 items-center justify-center rounded-full text-danger transition hover:bg-danger-soft disabled:opacity-50"
                  aria-label={`Borrar cuenta de ${user.email}`}
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              )}
            </div>
            <div className="flex gap-4 text-xs text-muted">
              <span className="flex items-center gap-1">
                <Landmark className="h-3.5 w-3.5" />
                {user.bank_connections_count}
              </span>
              <span className="flex items-center gap-1">
                <ListOrdered className="h-3.5 w-3.5" />
                {user.transactions_count}
              </span>
              <span className="flex items-center gap-1">
                <Users className="h-3.5 w-3.5" />
                {user.debtors_count}
              </span>
              <span className="ml-auto">{new Date(user.created_at).toLocaleDateString("es-ES")}</span>
            </div>
          </li>
        ))}
      </ul>
    </main>
  );
}

export default function AdminPage() {
  return (
    <AuthGuard>
      <AdminContent />
    </AuthGuard>
  );
}
