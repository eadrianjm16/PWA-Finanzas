"use client";

import { useCallback, useEffect, useState } from "react";
import AuthGuard from "@/components/AuthGuard";
import { apiFetch, ApiError } from "@/lib/api";
import { formatMoney } from "@/lib/format";
import type { Budget } from "@/lib/types";

function BudgetsContent() {
  const [budgets, setBudgets] = useState<Budget[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [draftLimit, setDraftLimit] = useState("");
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    try {
      const data = await apiFetch<Budget[]>("/api/budgets");
      setBudgets(data);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudieron cargar los presupuestos");
    }
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    load();
  }, [load]);

  function startEdit(budget: Budget) {
    setEditingId(budget.category.id);
    setDraftLimit(budget.monthly_limit != null ? String(budget.monthly_limit) : "");
  }

  async function save(categoryId: string) {
    const value = Number(draftLimit);
    if (!Number.isFinite(value) || value <= 0) {
      setError("Introduce un importe válido");
      return;
    }
    setSaving(true);
    setError(null);
    try {
      await apiFetch(`/api/budgets/${categoryId}`, {
        method: "PUT",
        body: JSON.stringify({ monthly_limit: value }),
      });
      setEditingId(null);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo guardar el presupuesto");
    } finally {
      setSaving(false);
    }
  }

  async function remove(categoryId: string) {
    setSaving(true);
    setError(null);
    try {
      await apiFetch(`/api/budgets/${categoryId}`, { method: "DELETE" });
      setEditingId(null);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo quitar el presupuesto");
    } finally {
      setSaving(false);
    }
  }

  return (
    <main className="mx-auto max-w-lg px-4 pb-24 pt-6">
      <h1 className="mb-6 text-xl font-semibold">Presupuestos</h1>

      {error && <p className="mb-4 text-sm text-red-600">{error}</p>}
      {budgets === null && <p className="text-sm text-neutral-500">Cargando…</p>}

      <ul className="divide-y divide-neutral-100 overflow-hidden rounded-xl border border-neutral-200 dark:divide-neutral-800 dark:border-neutral-800">
        {budgets?.map((budget) => {
          const isEditing = editingId === budget.category.id;
          const ratio =
            budget.monthly_limit && budget.monthly_limit > 0
              ? Math.min(budget.spent_this_month / budget.monthly_limit, 1)
              : 0;
          const over = budget.monthly_limit != null && budget.spent_this_month > budget.monthly_limit;

          return (
            <li key={budget.category.id} className="px-4 py-3">
              <button
                onClick={() => (isEditing ? setEditingId(null) : startEdit(budget))}
                className="flex w-full items-center justify-between text-left"
              >
                <span className="text-sm font-medium">{budget.category.name}</span>
                <span className="text-xs text-neutral-500">
                  {budget.monthly_limit != null
                    ? `${formatMoney(budget.spent_this_month, "EUR")} / ${formatMoney(budget.monthly_limit, "EUR")}`
                    : "Sin límite"}
                </span>
              </button>

              {budget.monthly_limit != null && (
                <div className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-neutral-100 dark:bg-neutral-800">
                  <div
                    className={`h-full rounded-full ${over ? "bg-red-500" : "bg-neutral-900 dark:bg-white"}`}
                    style={{ width: `${ratio * 100}%` }}
                  />
                </div>
              )}

              {isEditing && (
                <div className="mt-3 flex items-center gap-2">
                  <input
                    type="number"
                    inputMode="decimal"
                    autoFocus
                    value={draftLimit}
                    onChange={(e) => setDraftLimit(e.target.value)}
                    placeholder="Límite mensual (EUR)"
                    className="flex-1 rounded-lg border border-neutral-300 px-3 py-2 text-sm outline-none dark:border-neutral-700 dark:bg-neutral-900"
                  />
                  <button
                    onClick={() => save(budget.category.id)}
                    disabled={saving}
                    className="rounded-lg bg-neutral-900 px-3 py-2 text-sm font-medium text-white disabled:opacity-50 dark:bg-white dark:text-neutral-900"
                  >
                    Guardar
                  </button>
                  {budget.monthly_limit != null && (
                    <button
                      onClick={() => remove(budget.category.id)}
                      disabled={saving}
                      className="rounded-lg px-3 py-2 text-sm text-red-600 disabled:opacity-50"
                    >
                      Quitar
                    </button>
                  )}
                </div>
              )}
            </li>
          );
        })}
      </ul>
    </main>
  );
}

export default function BudgetsPage() {
  return (
    <AuthGuard>
      <BudgetsContent />
    </AuthGuard>
  );
}
