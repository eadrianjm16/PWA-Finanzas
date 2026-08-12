"use client";

import Link from "next/link";
import { useState } from "react";
import useSWR from "swr";
import { ChevronRight, Plus, Trash2, Users } from "lucide-react";
import AuthGuard from "@/components/AuthGuard";
import { SkeletonList } from "@/components/Skeleton";
import { apiFetch, ApiError } from "@/lib/api";
import { formatMoney } from "@/lib/format";
import type { Debtor } from "@/lib/types";

function balanceLabel(balance: number): string {
  if (balance > 0) return "Te debe";
  if (balance < 0) return "Le debes";
  return "Al día";
}

function balanceClass(balance: number): string {
  if (balance > 0) return "text-danger";
  if (balance < 0) return "text-warning";
  return "text-muted";
}

function initials(name: string): string {
  return name
    .trim()
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase())
    .join("");
}

function DeudoresContent() {
  const { data: debtors, mutate } = useSWR<Debtor[]>("/api/debtors", apiFetch);
  const totalBalance = (debtors ?? []).reduce((sum, d) => sum + d.balance, 0);
  const [error, setError] = useState<string | null>(null);
  const [adding, setAdding] = useState(false);
  const [newName, setNewName] = useState("");
  const [saving, setSaving] = useState(false);

  async function addDebtor() {
    const trimmed = newName.trim();
    if (!trimmed) return;
    setSaving(true);
    setError(null);
    try {
      await apiFetch("/api/debtors", { method: "POST", body: JSON.stringify({ name: trimmed }) });
      setNewName("");
      setAdding(false);
      await mutate();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo añadir");
    } finally {
      setSaving(false);
    }
  }

  async function deleteDebtor(debtor: Debtor, event: React.MouseEvent) {
    event.preventDefault();
    event.stopPropagation();
    if (!window.confirm(`¿Borrar a ${debtor.name}? Se perderá todo su historial.`)) return;
    try {
      await apiFetch(`/api/debtors/${debtor.id}`, { method: "DELETE" });
      await mutate();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo borrar");
    }
  }

  return (
    <main className="mx-auto max-w-lg px-4 pb-28 pt-6">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-semibold tracking-tight">Deudores</h1>
        <button
          onClick={() => setAdding((v) => !v)}
          className="flex items-center gap-1.5 rounded-full bg-brand px-4 py-2 text-sm font-medium text-brand-contrast shadow-[var(--shadow-card)] transition active:scale-95"
        >
          <Plus className="h-4 w-4" strokeWidth={2.5} />
          Persona
        </button>
      </div>

      {adding && (
        <div className="mb-4 flex items-center gap-2 rounded-2xl border border-surface-border bg-surface p-2 shadow-[var(--shadow-card)]">
          <input
            autoFocus
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            placeholder="Nombre"
            className="flex-1 rounded-xl border-none bg-transparent px-3 py-2 text-sm outline-none"
          />
          <button
            onClick={addDebtor}
            disabled={saving}
            className="rounded-xl bg-brand px-3 py-2 text-sm font-medium text-brand-contrast disabled:opacity-50"
          >
            Añadir
          </button>
        </div>
      )}

      {error && <p className="mb-4 text-sm text-danger">{error}</p>}
      {!debtors && <SkeletonList rows={4} />}
      {debtors?.length === 0 && (
        <div className="flex flex-col items-center rounded-2xl border border-dashed border-surface-border px-6 py-10 text-center">
          <span className="mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-brand-soft">
            <Users className="h-6 w-6 text-brand" />
          </span>
          <p className="text-sm text-muted">Sin deudores.</p>
          <p className="text-sm text-muted">Añade una persona con &quot;Persona&quot;.</p>
        </div>
      )}

      <ul className="mb-4 overflow-hidden rounded-2xl border border-surface-border bg-surface shadow-[var(--shadow-card)]">
        {debtors?.map((debtor, index) => (
          <li key={debtor.id} className={index > 0 ? "border-t border-surface-border" : ""}>
            <Link
              href={`/deudores/${debtor.id}`}
              className="flex items-center gap-3 px-4 py-3.5 transition hover:bg-surface-hover"
            >
              <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-brand-soft text-xs font-semibold text-brand">
                {initials(debtor.name)}
              </span>
              <span className="flex-1 text-sm font-medium">{debtor.name}</span>
              <div className="text-right">
                <p className="text-xs text-muted">{balanceLabel(debtor.balance)}</p>
                <p className={`tabular-nums text-sm font-semibold ${balanceClass(debtor.balance)}`}>
                  {formatMoney(Math.abs(debtor.balance), "EUR")}
                </p>
              </div>
              <button
                onClick={(e) => deleteDebtor(debtor, e)}
                className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-muted-soft transition hover:bg-danger-soft hover:text-danger"
                aria-label={`Borrar a ${debtor.name}`}
              >
                <Trash2 className="h-4 w-4" />
              </button>
              <ChevronRight className="h-4 w-4 shrink-0 text-muted-soft" />
            </Link>
          </li>
        ))}
      </ul>

      {debtors && debtors.length > 0 && (
        <div className="flex items-center justify-between rounded-2xl border border-surface-border bg-surface px-4 py-3.5 shadow-[var(--shadow-card)]">
          <span className="text-sm font-medium text-muted">Balance total</span>
          <div className="text-right">
            <p className="text-xs text-muted">{balanceLabel(totalBalance)}</p>
            <p className={`tabular-nums text-sm font-semibold ${balanceClass(totalBalance)}`}>
              {formatMoney(Math.abs(totalBalance), "EUR")}
            </p>
          </div>
        </div>
      )}
    </main>
  );
}

export default function DeudoresPage() {
  return (
    <AuthGuard>
      <DeudoresContent />
    </AuthGuard>
  );
}
