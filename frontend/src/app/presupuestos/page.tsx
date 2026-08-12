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
  const [draftRollover, setDraftRollover] = useState(false);
  const [saving, setSaving] = useState(false);

  function startEdit(budget: Budget) {
    setEditingId(budget.category.id);
    setDraftLimit(budget.monthly_limit != null ? String(budget.monthly_limit) : "");
    setDraftRollover(budget.rollover);
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
        body: JSON.stringify({ monthly_limit: value, rollover: draftRollover }),
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
          const limit = budget.effective_limit ?? budget.monthly_limit;
          const ratio = limit && limit > 0 ? Math.min(budget.spent_this_month / limit, 1) : 0;
          const over = limit != null && budget.spent_this_month > limit;
          const hasRolloverBonus = budget.rollover && limit != null && budget.monthly_limit != null && limit > budget.monthly_limit;

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
                  {limit != null
                    ? `${formatMoney(budget.spent_this_month, "EUR")} / ${formatMoney(limit, "EUR")}`
                    : "Sin límite"}
                </span>
              </button>

              {limit != null && (
                <div className="mt-2.5 h-2 w-full overflow-hidden rounded-full bg-surface-hover">
                  <div
                    className={`h-full rounded-full transition-all ${over ? "bg-danger" : "bg-brand"}`}
                    style={{ width: `${ratio * 100}%` }}
                  />
                </div>
              )}
              {hasRolloverBonus && (
                <p className="mt-1.5 text-[11px] text-muted">
                  {formatMoney(budget.monthly_limit ?? 0, "EUR")} + {formatMoney((limit ?? 0) - (budget.monthly_limit ?? 0), "EUR")} de remanente del mes pasado
                </p>
              )}

              {isEditing && (
                <div className="mt-3 flex flex-col gap-2">
                  <div className="flex items-center gap-2">
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
                  <label className="flex items-center gap-2 px-1 text-xs text-muted">
                    <input
                      type="checkbox"
                      checked={draftRollover}
                      onChange={(e) => setDraftRollover(e.target.checked)}
                      className="h-4 w-4 rounded border-surface-border accent-[var(--brand)]"
                    />
                    Sumar lo no gastado el mes pasado a este mes
                  </label>
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
