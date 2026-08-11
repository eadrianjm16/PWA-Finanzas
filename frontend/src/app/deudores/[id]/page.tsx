"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useState } from "react";
import useSWR, { mutate as globalMutate } from "swr";
import AuthGuard from "@/components/AuthGuard";
import { apiFetch, ApiError } from "@/lib/api";
import { formatMoney } from "@/lib/format";
import type { DebtorDetail } from "@/lib/types";

type EntryKind = "owedToMe" | "iOwe";

function DeudorDetailContent() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const debtorId = params.id;

  const { data: debtor, mutate } = useSWR<DebtorDetail>(`/api/debtors/${debtorId}`, apiFetch);
  const [error, setError] = useState<string | null>(null);
  const [panel, setPanel] = useState<"none" | "payment" | "manual">("none");
  const [amountText, setAmountText] = useState("");
  const [noteText, setNoteText] = useState("");
  const [kind, setKind] = useState<EntryKind>("owedToMe");
  const [saving, setSaving] = useState(false);

  async function reloadAfterMutation() {
    await mutate();
    await globalMutate("/api/debtors");
  }

  const isOwedToMe = (debtor?.balance ?? 0) >= 0;

  function resetPanel() {
    setPanel("none");
    setAmountText("");
    setNoteText("");
    setKind("owedToMe");
  }

  async function registerPayment() {
    const amount = Number(amountText.replace(",", "."));
    if (!Number.isFinite(amount) || amount <= 0) {
      setError("Importe no válido");
      return;
    }
    setSaving(true);
    setError(null);
    try {
      await apiFetch(`/api/debtors/${debtorId}/payments`, { method: "POST", body: JSON.stringify({ amount }) });
      resetPanel();
      await reloadAfterMutation();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo registrar el pago");
    } finally {
      setSaving(false);
    }
  }

  async function addManualDebt() {
    const amount = Number(amountText.replace(",", "."));
    if (!Number.isFinite(amount) || amount <= 0) {
      setError("Importe no válido");
      return;
    }
    setSaving(true);
    setError(null);
    try {
      await apiFetch(`/api/debtors/${debtorId}/entries`, {
        method: "POST",
        body: JSON.stringify({
          amount: kind === "owedToMe" ? amount : -amount,
          note: noteText.trim() || (kind === "owedToMe" ? "Deuda" : "Deuda (le debo)"),
        }),
      });
      resetPanel();
      await reloadAfterMutation();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo añadir la deuda");
    } finally {
      setSaving(false);
    }
  }

  async function cancelDebt() {
    if (!window.confirm(`Se registrará un ajuste para dejar el saldo con ${debtor?.name} en 0,00 €. ¿Continuar?`)) return;
    setError(null);
    try {
      await apiFetch(`/api/debtors/${debtorId}/cancel`, { method: "POST" });
      await reloadAfterMutation();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo cancelar la deuda");
    }
  }

  async function deleteDebtor() {
    if (!window.confirm(`¿Borrar a ${debtor?.name}? Se perderá todo su historial.`)) return;
    try {
      await apiFetch(`/api/debtors/${debtorId}`, { method: "DELETE" });
      await globalMutate("/api/debtors");
      router.push("/deudores");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo borrar");
    }
  }

  async function deleteEntry(entryId: string) {
    try {
      await apiFetch(`/api/debtors/${debtorId}/entries/${entryId}`, { method: "DELETE" });
      await reloadAfterMutation();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo borrar el movimiento");
    }
  }

  if (!debtor) {
    return (
      <main className="mx-auto max-w-lg px-4 pb-24 pt-6">
        <Link href="/deudores" className="text-sm text-neutral-500">
          ‹ Deudores
        </Link>
        {error ? <p className="mt-4 text-sm text-red-600">{error}</p> : <p className="mt-4 text-sm text-neutral-500">Cargando…</p>}
      </main>
    );
  }

  return (
    <main className="mx-auto max-w-lg px-4 pb-24 pt-6">
      <Link href="/deudores" className="text-sm text-neutral-500">
        ‹ Deudores
      </Link>

      <div className="mb-6 mt-2 flex items-center justify-between">
        <h1 className="text-xl font-semibold">{debtor.name}</h1>
        <button onClick={deleteDebtor} className="text-sm text-red-600">
          Borrar
        </button>
      </div>

      <div className="mb-6 flex items-center justify-between rounded-xl border border-neutral-200 px-4 py-3 dark:border-neutral-800">
        <span className="text-sm font-medium">{debtor.balance > 0 ? "Te debe" : debtor.balance < 0 ? "Le debes" : "Al día"}</span>
        <span
          className={`text-lg font-semibold ${
            debtor.balance > 0 ? "text-red-600" : debtor.balance < 0 ? "text-amber-600" : "text-neutral-500"
          }`}
        >
          {formatMoney(Math.abs(debtor.balance), "EUR")}
        </span>
      </div>

      {error && <p className="mb-4 text-sm text-red-600">{error}</p>}

      <div className="mb-6 flex flex-col gap-2">
        <button
          onClick={() => setPanel(panel === "payment" ? "none" : "payment")}
          disabled={debtor.balance === 0}
          className="rounded-xl border border-neutral-200 px-4 py-3 text-left text-sm font-medium disabled:opacity-40 dark:border-neutral-800"
        >
          {isOwedToMe ? "Registrar pago recibido" : "Registrar pago realizado"}
        </button>
        {panel === "payment" && (
          <div className="flex items-center gap-2 px-1">
            <input
              autoFocus
              type="number"
              inputMode="decimal"
              value={amountText}
              onChange={(e) => setAmountText(e.target.value)}
              placeholder="Importe"
              className="flex-1 rounded-lg border border-neutral-300 px-3 py-2 text-sm outline-none dark:border-neutral-700 dark:bg-neutral-900"
            />
            <button
              onClick={registerPayment}
              disabled={saving}
              className="rounded-lg bg-neutral-900 px-3 py-2 text-sm font-medium text-white disabled:opacity-50 dark:bg-white dark:text-neutral-900"
            >
              Registrar
            </button>
          </div>
        )}

        <button
          onClick={() => setPanel(panel === "manual" ? "none" : "manual")}
          className="rounded-xl border border-neutral-200 px-4 py-3 text-left text-sm font-medium dark:border-neutral-800"
        >
          Añadir deuda manual
        </button>
        {panel === "manual" && (
          <div className="flex flex-col gap-2 px-1">
            <div className="flex overflow-hidden rounded-lg border border-neutral-300 text-sm dark:border-neutral-700">
              <button
                onClick={() => setKind("owedToMe")}
                className={`flex-1 py-2 ${kind === "owedToMe" ? "bg-neutral-900 text-white dark:bg-white dark:text-neutral-900" : ""}`}
              >
                Deuda a cobrar
              </button>
              <button
                onClick={() => setKind("iOwe")}
                className={`flex-1 py-2 ${kind === "iOwe" ? "bg-neutral-900 text-white dark:bg-white dark:text-neutral-900" : ""}`}
              >
                Deuda a pagar
              </button>
            </div>
            <input
              type="number"
              inputMode="decimal"
              value={amountText}
              onChange={(e) => setAmountText(e.target.value)}
              placeholder="Importe"
              className="rounded-lg border border-neutral-300 px-3 py-2 text-sm outline-none dark:border-neutral-700 dark:bg-neutral-900"
            />
            <input
              value={noteText}
              onChange={(e) => setNoteText(e.target.value)}
              placeholder="Nota (opcional)"
              className="rounded-lg border border-neutral-300 px-3 py-2 text-sm outline-none dark:border-neutral-700 dark:bg-neutral-900"
            />
            <button
              onClick={addManualDebt}
              disabled={saving}
              className="rounded-lg bg-neutral-900 px-3 py-2 text-sm font-medium text-white disabled:opacity-50 dark:bg-white dark:text-neutral-900"
            >
              Añadir
            </button>
          </div>
        )}

        <button
          onClick={cancelDebt}
          disabled={debtor.balance === 0}
          className="rounded-xl border border-red-200 px-4 py-3 text-left text-sm font-medium text-red-600 disabled:opacity-40 dark:border-red-900"
        >
          Marcar deuda como cancelada
        </button>
      </div>

      <h2 className="mb-2 text-sm font-medium text-neutral-500">Historial</h2>
      {debtor.entries.length === 0 && <p className="text-sm text-neutral-500">Sin movimientos todavía</p>}
      <ul className="divide-y divide-neutral-100 overflow-hidden rounded-xl border border-neutral-200 dark:divide-neutral-800 dark:border-neutral-800">
        {debtor.entries.map((entry) => (
          <li key={entry.id} className="flex items-center justify-between px-4 py-3">
            <div className="min-w-0 pr-3">
              <p className="truncate text-sm">{entry.note ?? "Movimiento"}</p>
              <p className="text-xs text-neutral-500">{new Date(entry.date).toLocaleDateString("es-ES")}</p>
            </div>
            <div className="flex shrink-0 items-center gap-3">
              <span className={`text-sm font-medium ${entry.amount >= 0 ? "text-neutral-900 dark:text-neutral-100" : "text-amber-600"}`}>
                {entry.amount >= 0 ? "+" : "-"}
                {formatMoney(Math.abs(entry.amount), "EUR")}
              </span>
              <button onClick={() => deleteEntry(entry.id)} className="text-xs text-neutral-400" aria-label="Borrar movimiento">
                ✕
              </button>
            </div>
          </li>
        ))}
      </ul>
    </main>
  );
}

export default function DeudorDetailPage() {
  return (
    <AuthGuard>
      <DeudorDetailContent />
    </AuthGuard>
  );
}
