"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useState } from "react";
import useSWR, { mutate as globalMutate } from "swr";
import { Ban, ChevronLeft, Contact, HandCoins, Pencil, Phone, Plus, Trash2, X } from "lucide-react";
import AuthGuard from "@/components/AuthGuard";
import { Skeleton } from "@/components/Skeleton";
import { apiFetch, ApiError } from "@/lib/api";
import { formatMoney } from "@/lib/format";
import type { DebtorDetail } from "@/lib/types";
import { isContactPickerSupported, pickPhoneContact } from "@/lib/whatsapp";

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
  const [editingPhone, setEditingPhone] = useState(false);
  const [phoneDraft, setPhoneDraft] = useState("");

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

  async function savePhone() {
    setSaving(true);
    setError(null);
    try {
      await apiFetch(`/api/debtors/${debtorId}`, {
        method: "PATCH",
        body: JSON.stringify({ phone: phoneDraft.trim() || null }),
      });
      setEditingPhone(false);
      await reloadAfterMutation();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo guardar el teléfono");
    } finally {
      setSaving(false);
    }
  }

  async function pickFromContacts() {
    const picked = await pickPhoneContact();
    if (picked?.phone) setPhoneDraft(picked.phone);
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
      <main className="mx-auto max-w-lg px-4 pb-28 pt-6">
        <Link href="/deudores" className="flex items-center gap-1 text-sm font-medium text-muted">
          <ChevronLeft className="h-4 w-4" />
          Deudores
        </Link>
        {error ? (
          <p className="mt-4 text-sm text-danger">{error}</p>
        ) : (
          <div className="mt-4 flex flex-col gap-4">
            <Skeleton className="h-16 w-full" />
            <Skeleton className="h-32 w-full" />
          </div>
        )}
      </main>
    );
  }

  return (
    <main className="mx-auto max-w-lg px-4 pb-28 pt-6">
      <Link href="/deudores" className="flex items-center gap-1 text-sm font-medium text-muted">
        <ChevronLeft className="h-4 w-4" />
        Deudores
      </Link>

      <div className="mb-6 mt-3 flex items-center justify-between">
        <h1 className="text-2xl font-semibold tracking-tight">{debtor.name}</h1>
        <button onClick={deleteDebtor} className="flex items-center gap-1 text-sm font-medium text-danger">
          <Trash2 className="h-3.5 w-3.5" />
          Borrar
        </button>
      </div>

      <div className="mb-6 rounded-2xl bg-gradient-to-br from-brand to-brand-dark p-5 text-brand-contrast shadow-[var(--shadow-pop)]">
        <p className="mb-1 text-sm font-medium text-white/70">
          {debtor.balance > 0 ? "Te debe" : debtor.balance < 0 ? "Le debes" : "Al día"}
        </p>
        <p className="tabular-nums text-3xl font-semibold tracking-tight">
          {formatMoney(Math.abs(debtor.balance), "EUR")}
        </p>
      </div>

      <div className="mb-6 rounded-2xl border border-surface-border bg-surface p-3.5 shadow-[var(--shadow-card)]">
        {editingPhone ? (
          <div className="flex flex-col gap-2">
            {isContactPickerSupported() && (
              <button
                onClick={pickFromContacts}
                className="flex items-center justify-center gap-1.5 rounded-xl border border-surface-border bg-background px-3 py-2 text-sm font-medium text-brand"
              >
                <Contact className="h-4 w-4" />
                Elegir de contactos
              </button>
            )}
            <input
              autoFocus
              value={phoneDraft}
              onChange={(e) => setPhoneDraft(e.target.value)}
              placeholder="+34 612 345 678"
              className="rounded-xl border border-surface-border bg-background px-3 py-2 text-sm outline-none focus:border-brand focus:ring-4 focus:ring-brand-soft"
            />
            <div className="flex gap-2">
              <button
                onClick={savePhone}
                disabled={saving}
                className="flex-1 rounded-xl bg-brand px-3 py-2 text-sm font-medium text-brand-contrast disabled:opacity-50"
              >
                Guardar
              </button>
              <button
                onClick={() => setEditingPhone(false)}
                className="rounded-xl border border-surface-border px-3 py-2 text-sm font-medium"
              >
                Cancelar
              </button>
            </div>
          </div>
        ) : (
          <button
            onClick={() => {
              setPhoneDraft(debtor.phone ?? "");
              setEditingPhone(true);
            }}
            className="flex w-full items-center justify-between text-sm"
          >
            <span className="flex items-center gap-2 text-muted">
              <Phone className="h-4 w-4" />
              {debtor.phone ?? "Sin teléfono"}
            </span>
            <Pencil className="h-3.5 w-3.5 text-muted-soft" />
          </button>
        )}
      </div>

      {error && <p className="mb-4 text-sm text-danger">{error}</p>}

      <div className="mb-6 flex flex-col gap-2">
        <button
          onClick={() => setPanel(panel === "payment" ? "none" : "payment")}
          disabled={debtor.balance === 0}
          className="flex items-center gap-3 rounded-2xl border border-surface-border bg-surface px-4 py-3.5 text-left text-sm font-medium shadow-[var(--shadow-card)] disabled:opacity-40"
        >
          <HandCoins className="h-4 w-4 text-brand" />
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
              className="flex-1 rounded-xl border border-surface-border bg-surface px-3 py-2 text-sm outline-none focus:border-brand focus:ring-4 focus:ring-brand-soft"
            />
            <button
              onClick={registerPayment}
              disabled={saving}
              className="rounded-xl bg-brand px-3 py-2 text-sm font-medium text-brand-contrast disabled:opacity-50"
            >
              Registrar
            </button>
          </div>
        )}

        <button
          onClick={() => setPanel(panel === "manual" ? "none" : "manual")}
          className="flex items-center gap-3 rounded-2xl border border-surface-border bg-surface px-4 py-3.5 text-left text-sm font-medium shadow-[var(--shadow-card)]"
        >
          <Plus className="h-4 w-4 text-brand" />
          Añadir deuda manual
        </button>
        {panel === "manual" && (
          <div className="flex flex-col gap-2 px-1">
            <div className="flex overflow-hidden rounded-xl border border-surface-border text-sm">
              <button
                onClick={() => setKind("owedToMe")}
                className={`flex-1 py-2 transition ${kind === "owedToMe" ? "bg-brand text-brand-contrast" : "bg-surface"}`}
              >
                Deuda a cobrar
              </button>
              <button
                onClick={() => setKind("iOwe")}
                className={`flex-1 py-2 transition ${kind === "iOwe" ? "bg-brand text-brand-contrast" : "bg-surface"}`}
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
              className="rounded-xl border border-surface-border bg-surface px-3 py-2 text-sm outline-none focus:border-brand focus:ring-4 focus:ring-brand-soft"
            />
            <input
              value={noteText}
              onChange={(e) => setNoteText(e.target.value)}
              placeholder="Nota (opcional)"
              className="rounded-xl border border-surface-border bg-surface px-3 py-2 text-sm outline-none focus:border-brand focus:ring-4 focus:ring-brand-soft"
            />
            <button
              onClick={addManualDebt}
              disabled={saving}
              className="rounded-xl bg-brand px-3 py-2 text-sm font-medium text-brand-contrast disabled:opacity-50"
            >
              Añadir
            </button>
          </div>
        )}

        <button
          onClick={cancelDebt}
          disabled={debtor.balance === 0}
          className="flex items-center gap-3 rounded-2xl border border-danger/20 bg-danger-soft px-4 py-3.5 text-left text-sm font-medium text-danger disabled:opacity-40"
        >
          <Ban className="h-4 w-4" />
          Marcar deuda como cancelada
        </button>
      </div>

      <h2 className="mb-2 px-1 text-sm font-semibold text-muted">Historial</h2>
      {debtor.entries.length === 0 && <p className="px-1 text-sm text-muted">Sin movimientos todavía</p>}
      <ul className="overflow-hidden rounded-2xl border border-surface-border bg-surface shadow-[var(--shadow-card)]">
        {debtor.entries.map((entry, index) => (
          <li
            key={entry.id}
            className={`flex items-center justify-between px-4 py-3.5 ${index > 0 ? "border-t border-surface-border" : ""}`}
          >
            <div className="min-w-0 pr-3">
              <p className="truncate text-sm font-medium">{entry.note ?? "Movimiento"}</p>
              <p className="text-xs text-muted">{new Date(entry.date).toLocaleDateString("es-ES")}</p>
            </div>
            <div className="flex shrink-0 items-center gap-2">
              <span className={`tabular-nums text-sm font-semibold ${entry.amount >= 0 ? "text-foreground" : "text-warning"}`}>
                {entry.amount >= 0 ? "+" : "-"}
                {formatMoney(Math.abs(entry.amount), "EUR")}
              </span>
              <button
                onClick={() => deleteEntry(entry.id)}
                className="flex h-7 w-7 items-center justify-center rounded-full text-muted-soft transition hover:bg-surface-hover"
                aria-label="Borrar movimiento"
              >
                <X className="h-3.5 w-3.5" />
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
