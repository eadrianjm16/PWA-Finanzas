"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import AuthGuard from "@/components/AuthGuard";
import { apiFetch, ApiError } from "@/lib/api";
import { formatMoney } from "@/lib/format";
import type { Debtor } from "@/lib/types";

function balanceLabel(balance: number): string {
  if (balance > 0) return "Te debe";
  if (balance < 0) return "Le debes";
  return "Al día";
}

function balanceClass(balance: number): string {
  if (balance > 0) return "text-red-600";
  if (balance < 0) return "text-amber-600";
  return "text-neutral-500";
}

function DeudoresContent() {
  const [debtors, setDebtors] = useState<Debtor[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [adding, setAdding] = useState(false);
  const [newName, setNewName] = useState("");
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    try {
      const data = await apiFetch<Debtor[]>("/api/debtors");
      setDebtors(data);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudieron cargar los deudores");
    }
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    load();
  }, [load]);

  async function addDebtor() {
    const trimmed = newName.trim();
    if (!trimmed) return;
    setSaving(true);
    setError(null);
    try {
      await apiFetch("/api/debtors", { method: "POST", body: JSON.stringify({ name: trimmed }) });
      setNewName("");
      setAdding(false);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo añadir");
    } finally {
      setSaving(false);
    }
  }

  return (
    <main className="mx-auto max-w-lg px-4 pb-24 pt-6">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-xl font-semibold">Deudores</h1>
        <button
          onClick={() => setAdding((v) => !v)}
          className="rounded-full bg-neutral-900 px-4 py-2 text-sm font-medium text-white dark:bg-white dark:text-neutral-900"
        >
          + Persona
        </button>
      </div>

      {adding && (
        <div className="mb-4 flex items-center gap-2">
          <input
            autoFocus
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            placeholder="Nombre"
            className="flex-1 rounded-lg border border-neutral-300 px-3 py-2 text-sm outline-none dark:border-neutral-700 dark:bg-neutral-900"
          />
          <button
            onClick={addDebtor}
            disabled={saving}
            className="rounded-lg bg-neutral-900 px-3 py-2 text-sm font-medium text-white disabled:opacity-50 dark:bg-white dark:text-neutral-900"
          >
            Añadir
          </button>
        </div>
      )}

      {error && <p className="mb-4 text-sm text-red-600">{error}</p>}
      {debtors === null && <p className="text-sm text-neutral-500">Cargando…</p>}
      {debtors?.length === 0 && (
        <p className="text-sm text-neutral-500">Sin deudores. Añade una persona con &quot;+ Persona&quot;.</p>
      )}

      <ul className="divide-y divide-neutral-100 overflow-hidden rounded-xl border border-neutral-200 dark:divide-neutral-800 dark:border-neutral-800">
        {debtors?.map((debtor) => (
          <li key={debtor.id}>
            <Link href={`/deudores/${debtor.id}`} className="flex items-center justify-between px-4 py-3">
              <span className="text-sm font-medium">{debtor.name}</span>
              <div className="text-right">
                <p className="text-xs text-neutral-500">{balanceLabel(debtor.balance)}</p>
                <p className={`text-sm font-semibold ${balanceClass(debtor.balance)}`}>
                  {formatMoney(Math.abs(debtor.balance), "EUR")}
                </p>
              </div>
            </Link>
          </li>
        ))}
      </ul>
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
