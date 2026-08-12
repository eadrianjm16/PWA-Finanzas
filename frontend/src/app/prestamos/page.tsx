"use client";

import { useState } from "react";
import useSWR from "swr";
import { CreditCard, Pencil, Plus, Trash2 } from "lucide-react";
import AuthGuard from "@/components/AuthGuard";
import { SkeletonList } from "@/components/Skeleton";
import { apiFetch, ApiError } from "@/lib/api";
import { formatMoney } from "@/lib/format";
import type { Loan } from "@/lib/types";

interface LoanPayload {
  name: string;
  credit_limit: number | null;
  balance: number;
  monthly_payment: number;
  tin: number | null;
  tae: number | null;
  next_payment_date: string | null;
}

function toDateInputValue(iso: string | null): string {
  return iso ? iso.slice(0, 10) : "";
}

function formatDate(iso: string | null): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString("es-ES", { day: "numeric", month: "short", year: "numeric" });
}

function LoanForm({
  initial,
  onCancel,
  onSubmit,
  saving,
  error,
}: {
  initial?: Loan;
  onCancel: () => void;
  onSubmit: (payload: LoanPayload) => void;
  saving: boolean;
  error: string | null;
}) {
  const [name, setName] = useState(initial?.name ?? "");
  const [creditLimit, setCreditLimit] = useState(initial?.credit_limit != null ? String(initial.credit_limit) : "");
  const [balance, setBalance] = useState(initial?.balance != null ? String(initial.balance) : "");
  const [monthlyPayment, setMonthlyPayment] = useState(
    initial?.monthly_payment != null ? String(initial.monthly_payment) : ""
  );
  const [tin, setTin] = useState(initial?.tin != null ? String(initial.tin) : "");
  const [tae, setTae] = useState(initial?.tae != null ? String(initial.tae) : "");
  const [nextPaymentDate, setNextPaymentDate] = useState(toDateInputValue(initial?.next_payment_date ?? null));

  function submit() {
    const balanceValue = Number(balance);
    const paymentValue = Number(monthlyPayment);
    if (!name.trim() || Number.isNaN(balanceValue) || balanceValue < 0 || Number.isNaN(paymentValue) || paymentValue < 0) {
      return;
    }
    onSubmit({
      name: name.trim(),
      credit_limit: creditLimit.trim() ? Number(creditLimit) : null,
      balance: balanceValue,
      monthly_payment: paymentValue,
      tin: tin.trim() ? Number(tin) : null,
      tae: tae.trim() ? Number(tae) : null,
      next_payment_date: nextPaymentDate ? new Date(nextPaymentDate).toISOString() : null,
    });
  }

  return (
    <div className="mb-4 flex flex-col gap-2 rounded-2xl border border-surface-border bg-surface p-3 shadow-[var(--shadow-card)]">
      {!initial && (
        <input
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Nombre (ej. Cofidis - Crédito Directo)"
          className="rounded-xl border border-surface-border bg-background px-3 py-2 text-sm outline-none focus:border-brand focus:ring-4 focus:ring-brand-soft"
        />
      )}
      <div className="flex gap-2">
        <label className="flex flex-1 flex-col gap-1">
          <span className="text-xs text-muted">Saldo pendiente</span>
          <input
            type="number"
            inputMode="decimal"
            value={balance}
            onChange={(e) => setBalance(e.target.value)}
            placeholder="Importe"
            className="rounded-xl border border-surface-border bg-background px-3 py-2 text-sm outline-none focus:border-brand focus:ring-4 focus:ring-brand-soft"
          />
        </label>
        <label className="flex flex-1 flex-col gap-1">
          <span className="text-xs text-muted">Cuota mensual</span>
          <input
            type="number"
            inputMode="decimal"
            value={monthlyPayment}
            onChange={(e) => setMonthlyPayment(e.target.value)}
            placeholder="Importe"
            className="rounded-xl border border-surface-border bg-background px-3 py-2 text-sm outline-none focus:border-brand focus:ring-4 focus:ring-brand-soft"
          />
        </label>
      </div>
      <div className="flex gap-2">
        <label className="flex flex-1 flex-col gap-1">
          <span className="text-xs text-muted">Línea máxima (opcional)</span>
          <input
            type="number"
            inputMode="decimal"
            value={creditLimit}
            onChange={(e) => setCreditLimit(e.target.value)}
            placeholder="Importe"
            className="rounded-xl border border-surface-border bg-background px-3 py-2 text-sm outline-none focus:border-brand focus:ring-4 focus:ring-brand-soft"
          />
        </label>
        <label className="flex w-28 flex-col gap-1">
          <span className="text-xs text-muted">Próximo pago</span>
          <input
            type="date"
            value={nextPaymentDate}
            onChange={(e) => setNextPaymentDate(e.target.value)}
            className="rounded-xl border border-surface-border bg-background px-2 py-2 text-sm outline-none focus:border-brand focus:ring-4 focus:ring-brand-soft"
          />
        </label>
      </div>
      <div className="flex gap-2">
        <label className="flex flex-1 flex-col gap-1">
          <span className="text-xs text-muted">TIN % (opcional)</span>
          <input
            type="number"
            inputMode="decimal"
            value={tin}
            onChange={(e) => setTin(e.target.value)}
            placeholder="21.79"
            className="rounded-xl border border-surface-border bg-background px-3 py-2 text-sm outline-none focus:border-brand focus:ring-4 focus:ring-brand-soft"
          />
        </label>
        <label className="flex flex-1 flex-col gap-1">
          <span className="text-xs text-muted">TAE % (opcional)</span>
          <input
            type="number"
            inputMode="decimal"
            value={tae}
            onChange={(e) => setTae(e.target.value)}
            placeholder="16.02"
            className="rounded-xl border border-surface-border bg-background px-3 py-2 text-sm outline-none focus:border-brand focus:ring-4 focus:ring-brand-soft"
          />
        </label>
      </div>
      {error && <p className="text-sm text-danger">{error}</p>}
      <div className="flex gap-2">
        <button
          onClick={submit}
          disabled={saving}
          className="flex-1 rounded-xl bg-brand px-4 py-2 text-sm font-medium text-brand-contrast disabled:opacity-50"
        >
          {initial ? "Guardar cambios" : "Crear"}
        </button>
        <button onClick={onCancel} className="rounded-xl border border-surface-border px-4 py-2 text-sm font-medium">
          Cancelar
        </button>
      </div>
    </div>
  );
}

function LoanCard({ loan, onChanged }: { loan: Loan; onChanged: () => Promise<unknown> }) {
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const usageRatio = loan.credit_limit && loan.credit_limit > 0 ? Math.min(1, loan.balance / loan.credit_limit) : null;

  async function save(payload: LoanPayload) {
    setSaving(true);
    setError(null);
    try {
      await apiFetch(`/api/loans/${loan.id}`, { method: "PATCH", body: JSON.stringify(payload) });
      setEditing(false);
      await onChanged();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo actualizar el préstamo");
    } finally {
      setSaving(false);
    }
  }

  async function remove() {
    if (!window.confirm(`¿Borrar "${loan.name}" del seguimiento?`)) return;
    await apiFetch(`/api/loans/${loan.id}`, { method: "DELETE" });
    await onChanged();
  }

  if (editing) {
    return <LoanForm initial={loan} onCancel={() => setEditing(false)} onSubmit={save} saving={saving} error={error} />;
  }

  return (
    <li className="rounded-2xl border border-surface-border bg-surface p-4 shadow-[var(--shadow-card)]">
      <div className="mb-2 flex items-start justify-between">
        <div className="flex items-center gap-3">
          <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-brand-soft">
            <CreditCard className="h-4 w-4 text-brand" />
          </span>
          <div>
            <p className="text-sm font-medium">{loan.name}</p>
            <p className="text-xs text-muted">
              {formatMoney(loan.balance, "EUR")}
              {loan.credit_limit != null && ` de ${formatMoney(loan.credit_limit, "EUR")}`}
            </p>
          </div>
        </div>
        <div className="flex shrink-0 items-center gap-1">
          <button onClick={() => setEditing(true)} aria-label="Actualizar extracto" className="text-muted-soft">
            <Pencil className="h-4 w-4" />
          </button>
          <button onClick={remove} aria-label="Borrar préstamo" className="text-danger">
            <Trash2 className="h-4 w-4" />
          </button>
        </div>
      </div>

      {usageRatio != null && (
        <div className="mb-3 h-2 w-full overflow-hidden rounded-full bg-surface-hover">
          <div
            className={`h-full rounded-full transition-all ${usageRatio >= 0.9 ? "bg-danger" : "bg-brand"}`}
            style={{ width: `${usageRatio * 100}%` }}
          />
        </div>
      )}

      <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-muted">
        <span>Cuota: {formatMoney(loan.monthly_payment, "EUR")}/mes</span>
        <span>Próximo pago: {formatDate(loan.next_payment_date)}</span>
        {loan.tin != null && <span>TIN {loan.tin}%</span>}
        {loan.tae != null && <span>TAE {loan.tae}%</span>}
      </div>
    </li>
  );
}

function PrestamosContent() {
  const { data: loans, mutate } = useSWR<Loan[]>("/api/loans", apiFetch);
  const [creating, setCreating] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const totalBalance = (loans ?? []).reduce((sum, loan) => sum + loan.balance, 0);

  async function create(payload: LoanPayload) {
    setSaving(true);
    setError(null);
    try {
      await apiFetch("/api/loans", { method: "POST", body: JSON.stringify(payload) });
      setCreating(false);
      await mutate();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo crear el préstamo");
    } finally {
      setSaving(false);
    }
  }

  return (
    <main className="mx-auto max-w-lg px-4 pb-28 pt-6">
      <div className="mb-1 flex items-center justify-between">
        <h1 className="text-2xl font-semibold tracking-tight">Préstamos</h1>
        <button
          onClick={() => setCreating(true)}
          className="flex items-center gap-1.5 rounded-full bg-brand px-4 py-2 text-sm font-medium text-brand-contrast shadow-[var(--shadow-card)] transition active:scale-95"
        >
          <Plus className="h-4 w-4" strokeWidth={2.5} />
          Nuevo
        </button>
      </div>
      <p className="mb-6 text-sm text-muted">
        Seguimiento manual de créditos y préstamos externos — actualízalo cuando llegue el extracto nuevo
      </p>

      {loans && loans.length > 0 && (
        <div className="mb-6 overflow-hidden rounded-2xl bg-gradient-to-br from-brand to-brand-dark p-6 text-brand-contrast shadow-[var(--shadow-pop)]">
          <p className="mb-1 text-sm font-medium text-white/70">Deuda total en créditos</p>
          <p className="tabular-nums text-4xl font-semibold tracking-tight">{formatMoney(totalBalance, "EUR")}</p>
        </div>
      )}

      {!loans && <SkeletonList rows={2} />}
      {loans?.length === 0 && !creating && (
        <div className="flex flex-col items-center rounded-2xl border border-dashed border-surface-border px-6 py-10 text-center">
          <p className="text-sm text-muted">Todavía no tienes ningún préstamo en seguimiento.</p>
        </div>
      )}

      {creating && <LoanForm onCancel={() => setCreating(false)} onSubmit={create} saving={saving} error={error} />}

      <ul className="flex flex-col gap-3">
        {loans?.map((loan) => (
          <LoanCard key={loan.id} loan={loan} onChanged={mutate} />
        ))}
      </ul>
    </main>
  );
}

export default function PrestamosPage() {
  return (
    <AuthGuard>
      <PrestamosContent />
    </AuthGuard>
  );
}
