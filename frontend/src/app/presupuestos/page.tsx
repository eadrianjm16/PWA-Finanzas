"use client";

import { useState } from "react";
import useSWR from "swr";
import AuthGuard from "@/components/AuthGuard";
import { SkeletonList } from "@/components/Skeleton";
import { CategoryIcon } from "@/lib/icons";
import { apiFetch, ApiError } from "@/lib/api";
import { formatMoney } from "@/lib/format";
import type { Budget } from "@/lib/types";

function BudgetsContent() {
  const { data: budgets, mutate } = useSWR<Budget[]>("/api/budgets", apiFetch);
  const [error, setError] = useState<string | null>(null);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [draftLimit, setDraftLimit] = useState("");
  const [saving, setSaving] = useState(false);

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
      await mutate();
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
      await mutate();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo quitar el presupuesto");
    } finally {
      setSaving(false);
    }
  }

  return (
    <main className="mx-auto max-w-lg px-4 pb-28 pt-6">
      <h1 className="mb-6 text-2xl font-semibold tracking-tight">Presupuestos</h1>

      {error && <p className="mb-4 text-sm text-danger">{error}</p>}
      {!budgets && <SkeletonList rows={6} />}

      <ul className="overflow-hidden rounded-2xl border border-surface-border bg-surface shadow-[var(--shadow-card)]">
        {budgets?.map((budget, index) => {
          const isEditing = editingId === budget.category.id;
          const ratio =
            budget.monthly_limit && budget.monthly_limit > 0
              ? Math.min(budget.spent_this_month / budget.monthly_limit, 1)
              : 0;
          const over = budget.monthly_limit != null && budget.spent_this_month > budget.monthly_limit;

          return (
            <li key={budget.category.id} className={`px-4 py-3.5 ${index > 0 ? "border-t border-surface-border" : ""}`}>
              <button
                onClick={() => (isEditing ? setEditingId(null) : startEdit(budget))}
                className="flex w-full items-center gap-3 text-left"
              >
                <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-surface-hover">
                  <CategoryIcon name={budget.category.system_icon_name} className="h-4 w-4 text-muted" />
                </span>
                <span className="flex-1 text-sm font-medium">{budget.category.name}</span>
                <span className="tabular-nums shrink-0 text-xs text-muted">
                  {budget.monthly_limit != null
                    ? `${formatMoney(budget.spent_this_month, "EUR")} / ${formatMoney(budget.monthly_limit, "EUR")}`
                    : "Sin límite"}
                </span>
              </button>

              {budget.monthly_limit != null && (
                <div className="mt-2.5 h-2 w-full overflow-hidden rounded-full bg-surface-hover">
                  <div
                    className={`h-full rounded-full transition-all ${over ? "bg-danger" : "bg-brand"}`}
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
                    className="flex-1 rounded-xl border border-surface-border bg-background px-3 py-2 text-sm outline-none transition-colors focus:border-brand focus:ring-4 focus:ring-brand-soft"
                  />
                  <button
                    onClick={() => save(budget.category.id)}
                    disabled={saving}
                    className="rounded-xl bg-brand px-3 py-2 text-sm font-medium text-brand-contrast disabled:opacity-50"
                  >
                    Guardar
                  </button>
                  {budget.monthly_limit != null && (
                    <button
                      onClick={() => remove(budget.category.id)}
                      disabled={saving}
                      className="rounded-xl px-3 py-2 text-sm font-medium text-danger disabled:opacity-50"
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
