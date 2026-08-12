"use client";

import { useState } from "react";
import useSWR from "swr";
import { Check, Pencil, Plus, Trash2 } from "lucide-react";
import AuthGuard from "@/components/AuthGuard";
import { SkeletonList } from "@/components/Skeleton";
import { apiFetch, ApiError } from "@/lib/api";
import { formatMoney } from "@/lib/format";
import type { FixedExpense, FixedExpensesSummary } from "@/lib/types";

function SummaryCard({ summary, onChanged }: { summary: FixedExpensesSummary | undefined; onChanged: () => Promise<unknown> }) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState("");
  const [saving, setSaving] = useState(false);

  async function saveIncome() {
    const value = Number(draft);
    if (!value || value <= 0) return;
    setSaving(true);
    try {
      await apiFetch("/api/fixed-expenses/income-override", {
        method: "PUT",
        body: JSON.stringify({ monthly_amount: value }),
      });
      setEditing(false);
      setDraft("");
      await onChanged();
    } finally {
      setSaving(false);
    }
  }

  async function clearOverride() {
    setSaving(true);
    try {
      await apiFetch("/api/fixed-expenses/income-override", {
        method: "PUT",
        body: JSON.stringify({ monthly_amount: null }),
      });
      await onChanged();
    } finally {
      setSaving(false);
    }
  }

  if (!summary) return <SkeletonList rows={1} />;

  return (
    <div className="mb-6 rounded-2xl border border-surface-border bg-surface p-4 shadow-[var(--shadow-card)]">
      <div className="mb-3 flex items-center justify-between">
        <div>
          <p className="text-xs text-muted">
            Nómina {summary.income_is_manual ? "(manual)" : summary.estimated_income != null ? "(detectada)" : ""}
          </p>
          {editing ? (
            <div className="mt-1 flex items-center gap-2">
              <input
                type="number"
                inputMode="decimal"
                autoFocus
                value={draft}
                onChange={(e) => setDraft(e.target.value)}
                placeholder="Importe mensual"
                className="w-32 rounded-lg border border-surface-border bg-background px-2 py-1 text-sm outline-none focus:border-brand focus:ring-4 focus:ring-brand-soft"
              />
              <button onClick={saveIncome} disabled={saving} className="text-sm font-medium text-brand">
                Guardar
              </button>
              <button onClick={() => setEditing(false)} className="text-sm text-muted">
                Cancelar
              </button>
            </div>
          ) : (
            <div className="flex items-center gap-2">
              <p className="text-lg font-semibold tabular-nums">
                {summary.estimated_income != null ? formatMoney(summary.estimated_income, "EUR") : "Sin datos"}
              </p>
              <button onClick={() => setEditing(true)} aria-label="Editar nómina" className="text-muted-soft">
                <Pencil className="h-3.5 w-3.5" />
              </button>
            </div>
          )}
          {summary.income_is_manual && !editing && (
            <button onClick={clearOverride} className="mt-1 text-[11px] text-brand">
              Volver a la detectada automáticamente
            </button>
          )}
        </div>
      </div>

      <div className="flex items-center justify-between border-t border-surface-border pt-3 text-sm">
        <span className="text-muted">Gasto fijo total</span>
        <span className="tabular-nums font-medium">{formatMoney(summary.total_fixed, "EUR")}</span>
      </div>
      <div className="mt-1.5 flex items-center justify-between text-sm">
        <span className="text-muted">Sobrante estimado</span>
        <span
          className={`tabular-nums font-semibold ${
            summary.estimated_leftover == null ? "text-muted" : summary.estimated_leftover < 0 ? "text-danger" : "text-success"
          }`}
        >
          {summary.estimated_leftover != null ? formatMoney(summary.estimated_leftover, "EUR") : "—"}
        </span>
      </div>
    </div>
  );
}

function GastosFijosContent() {
  const { data: expenses, mutate } = useSWR<FixedExpense[]>("/api/fixed-expenses", apiFetch);
  const { data: summary, mutate: mutateSummary } = useSWR<FixedExpensesSummary>("/api/fixed-expenses/summary", apiFetch);
  const [creating, setCreating] = useState(false);
  const [name, setName] = useState("");
  const [amount, setAmount] = useState("");
  const [dueDay, setDueDay] = useState("1");
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  async function refreshAll() {
    await Promise.all([mutate(), mutateSummary()]);
  }

  async function toggle(expense: FixedExpense) {
    const optimistic = expenses?.map((e) => (e.id === expense.id ? { ...e, checked: !e.checked } : e));
    mutate(optimistic, { revalidate: false });
    try {
      await apiFetch(`/api/fixed-expenses/${expense.id}/check`, { method: expense.checked ? "DELETE" : "POST" });
    } finally {
      await mutate();
    }
  }

  async function createExpense() {
    const trimmed = name.trim();
    const amountValue = Number(amount);
    const dayValue = Number(dueDay);
    if (!trimmed || !amountValue || amountValue <= 0 || dayValue < 1 || dayValue > 31) return;
    setSaving(true);
    setError(null);
    try {
      await apiFetch("/api/fixed-expenses", {
        method: "POST",
        body: JSON.stringify({ name: trimmed, amount: amountValue, due_day: dayValue }),
      });
      setName("");
      setAmount("");
      setDueDay("1");
      setCreating(false);
      await refreshAll();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo crear el gasto fijo");
    } finally {
      setSaving(false);
    }
  }

  async function remove(expense: FixedExpense) {
    if (!window.confirm(`¿Borrar "${expense.name}"?`)) return;
    await apiFetch(`/api/fixed-expenses/${expense.id}`, { method: "DELETE" });
    await refreshAll();
  }

  const sorted = [...(expenses ?? [])].sort((a, b) => a.due_day - b.due_day);

  return (
    <main className="mx-auto max-w-lg px-4 pb-28 pt-6">
      <div className="mb-1 flex items-center justify-between">
        <h1 className="text-2xl font-semibold tracking-tight">Gasto Fijo</h1>
        <button
          onClick={() => setCreating(true)}
          className="flex items-center gap-1.5 rounded-full bg-brand px-4 py-2 text-sm font-medium text-brand-contrast shadow-[var(--shadow-card)] transition active:scale-95"
        >
          <Plus className="h-4 w-4" strokeWidth={2.5} />
          Nuevo
        </button>
      </div>
      <p className="mb-6 text-sm text-muted">Gestión manual — márcalo cuando lo pagues, se resetea cada mes</p>

      <SummaryCard summary={summary} onChanged={refreshAll} />

      {creating && (
        <div className="mb-4 flex flex-col gap-2 rounded-2xl border border-surface-border bg-surface p-3 shadow-[var(--shadow-card)]">
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Nombre (ej. Alquiler)"
            className="rounded-xl border border-surface-border bg-background px-3 py-2 text-sm outline-none focus:border-brand focus:ring-4 focus:ring-brand-soft"
          />
          <div className="flex gap-2">
            <input
              type="number"
              inputMode="decimal"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              placeholder="Importe"
              className="flex-1 rounded-xl border border-surface-border bg-background px-3 py-2 text-sm outline-none focus:border-brand focus:ring-4 focus:ring-brand-soft"
            />
            <input
              type="number"
              min={1}
              max={31}
              value={dueDay}
              onChange={(e) => setDueDay(e.target.value)}
              placeholder="Día"
              className="w-20 rounded-xl border border-surface-border bg-background px-3 py-2 text-sm outline-none focus:border-brand focus:ring-4 focus:ring-brand-soft"
            />
          </div>
          {error && <p className="text-sm text-danger">{error}</p>}
          <div className="flex gap-2">
            <button
              onClick={createExpense}
              disabled={saving}
              className="flex-1 rounded-xl bg-brand px-4 py-2 text-sm font-medium text-brand-contrast disabled:opacity-50"
            >
              Crear
            </button>
            <button
              onClick={() => setCreating(false)}
              className="rounded-xl border border-surface-border px-4 py-2 text-sm font-medium"
            >
              Cancelar
            </button>
          </div>
        </div>
      )}

      {!expenses && <SkeletonList rows={4} />}
      {expenses?.length === 0 && !creating && (
        <div className="flex flex-col items-center rounded-2xl border border-dashed border-surface-border px-6 py-10 text-center">
          <p className="text-sm text-muted">Todavía no has añadido ningún gasto fijo.</p>
        </div>
      )}

      <ul className="overflow-hidden rounded-2xl border border-surface-border bg-surface shadow-[var(--shadow-card)]">
        {sorted.map((expense, index) => (
          <li
            key={expense.id}
            className={`flex items-center gap-3 px-4 py-3.5 ${index > 0 ? "border-t border-surface-border" : ""}`}
          >
            <button
              onClick={() => toggle(expense)}
              aria-label={expense.checked ? "Marcar como pendiente" : "Marcar como pagado"}
              className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-full border-2 transition ${
                expense.checked ? "border-success bg-success text-white" : "border-surface-border"
              }`}
            >
              {expense.checked && <Check className="h-3.5 w-3.5" strokeWidth={3} />}
            </button>
            <div className="min-w-0 flex-1">
              <p className={`truncate text-sm font-medium ${expense.checked ? "text-muted line-through" : ""}`}>
                {expense.name}
              </p>
              <p className="text-xs text-muted">Día {expense.due_day} de cada mes</p>
            </div>
            <span className="tabular-nums shrink-0 text-sm font-semibold">{formatMoney(expense.amount, "EUR")}</span>
            <button onClick={() => remove(expense)} aria-label="Borrar gasto fijo" className="text-danger">
              <Trash2 className="h-4 w-4" />
            </button>
          </li>
        ))}
      </ul>
    </main>
  );
}

export default function GastosFijosPage() {
  return (
    <AuthGuard>
      <GastosFijosContent />
    </AuthGuard>
  );
}
