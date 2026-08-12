"use client";

import { useState } from "react";
import useSWR from "swr";
import { Plus, Target, Trash2 } from "lucide-react";
import AuthGuard from "@/components/AuthGuard";
import { SkeletonList } from "@/components/Skeleton";
import { apiFetch, ApiError } from "@/lib/api";
import { formatMoney } from "@/lib/format";
import type { SavingsGoal } from "@/lib/types";

function GoalCard({ goal, onChanged }: { goal: SavingsGoal; onChanged: () => Promise<unknown> }) {
  const [amount, setAmount] = useState("");
  const [busy, setBusy] = useState(false);
  const progress = goal.target_amount > 0 ? Math.min(1, goal.current_amount / goal.target_amount) : 0;

  async function contribute(sign: 1 | -1) {
    const value = Number(amount);
    if (!value || value <= 0) return;
    setBusy(true);
    try {
      await apiFetch(`/api/savings-goals/${goal.id}/contribute`, {
        method: "POST",
        body: JSON.stringify({ amount: value * sign }),
      });
      setAmount("");
      await onChanged();
    } finally {
      setBusy(false);
    }
  }

  async function remove() {
    if (!window.confirm(`¿Borrar la meta "${goal.name}"?`)) return;
    await apiFetch(`/api/savings-goals/${goal.id}`, { method: "DELETE" });
    await onChanged();
  }

  return (
    <li className="rounded-2xl border border-surface-border bg-surface p-4 shadow-[var(--shadow-card)]">
      <div className="mb-2 flex items-start justify-between">
        <div className="flex items-center gap-3">
          <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-brand-soft">
            <Target className="h-4 w-4 text-brand" />
          </span>
          <div>
            <p className="text-sm font-medium">{goal.name}</p>
            <p className="text-xs text-muted">
              {formatMoney(goal.current_amount, "EUR")} de {formatMoney(goal.target_amount, "EUR")}
            </p>
          </div>
        </div>
        <button onClick={remove} aria-label="Borrar meta" className="text-danger">
          <Trash2 className="h-4 w-4" />
        </button>
      </div>

      <div className="mb-3 h-2 w-full overflow-hidden rounded-full bg-surface-hover">
        <div
          className={`h-full rounded-full transition-all ${progress >= 1 ? "bg-success" : "bg-brand"}`}
          style={{ width: `${progress * 100}%` }}
        />
      </div>

      <div className="flex gap-2">
        <input
          type="number"
          inputMode="decimal"
          value={amount}
          onChange={(e) => setAmount(e.target.value)}
          placeholder="Importe"
          className="min-w-0 flex-1 rounded-xl border border-surface-border bg-background px-3 py-2 text-sm outline-none focus:border-brand focus:ring-4 focus:ring-brand-soft"
        />
        <button
          onClick={() => contribute(1)}
          disabled={busy}
          className="rounded-xl bg-brand px-3 py-2 text-sm font-medium text-brand-contrast disabled:opacity-50"
        >
          Añadir
        </button>
        <button
          onClick={() => contribute(-1)}
          disabled={busy}
          className="rounded-xl border border-surface-border px-3 py-2 text-sm font-medium disabled:opacity-50"
        >
          Retirar
        </button>
      </div>
    </li>
  );
}

function MetasContent() {
  const { data: goals, mutate } = useSWR<SavingsGoal[]>("/api/savings-goals", apiFetch);
  const [creating, setCreating] = useState(false);
  const [name, setName] = useState("");
  const [target, setTarget] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  async function createGoal() {
    const trimmed = name.trim();
    const targetValue = Number(target);
    if (!trimmed || !targetValue || targetValue <= 0) return;
    setSaving(true);
    setError(null);
    try {
      await apiFetch("/api/savings-goals", {
        method: "POST",
        body: JSON.stringify({ name: trimmed, target_amount: targetValue }),
      });
      setName("");
      setTarget("");
      setCreating(false);
      await mutate();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo crear la meta");
    } finally {
      setSaving(false);
    }
  }

  return (
    <main className="mx-auto max-w-lg px-4 pb-28 pt-6">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-semibold tracking-tight">Metas de ahorro</h1>
        <button
          onClick={() => setCreating(true)}
          className="flex items-center gap-1.5 rounded-full bg-brand px-4 py-2 text-sm font-medium text-brand-contrast shadow-[var(--shadow-card)] transition active:scale-95"
        >
          <Plus className="h-4 w-4" strokeWidth={2.5} />
          Nueva
        </button>
      </div>

      {!goals && <SkeletonList rows={3} />}
      {goals?.length === 0 && !creating && (
        <div className="flex flex-col items-center rounded-2xl border border-dashed border-surface-border px-6 py-10 text-center">
          <p className="text-sm text-muted">Todavía no tienes metas de ahorro.</p>
        </div>
      )}

      {creating && (
        <div className="mb-4 flex flex-col gap-2 rounded-2xl border border-surface-border bg-surface p-3 shadow-[var(--shadow-card)]">
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Nombre (ej. Viaje a Japón)"
            className="rounded-xl border border-surface-border bg-background px-3 py-2 text-sm outline-none focus:border-brand focus:ring-4 focus:ring-brand-soft"
          />
          <input
            type="number"
            inputMode="decimal"
            value={target}
            onChange={(e) => setTarget(e.target.value)}
            placeholder="Objetivo en €"
            className="rounded-xl border border-surface-border bg-background px-3 py-2 text-sm outline-none focus:border-brand focus:ring-4 focus:ring-brand-soft"
          />
          {error && <p className="text-sm text-danger">{error}</p>}
          <div className="flex gap-2">
            <button
              onClick={createGoal}
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

      <ul className="flex flex-col gap-3">
        {goals?.map((goal) => (
          <GoalCard key={goal.id} goal={goal} onChanged={mutate} />
        ))}
      </ul>
    </main>
  );
}

export default function MetasPage() {
  return (
    <AuthGuard>
      <MetasContent />
    </AuthGuard>
  );
}
