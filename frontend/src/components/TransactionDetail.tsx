"use client";

import { useEffect, useState } from "react";
import { Check, CheckCircle2, ChevronLeft, Circle, Split, Tag, X } from "lucide-react";
import { apiFetch, ApiError } from "@/lib/api";
import { formatMoney } from "@/lib/format";
import { CategoryIcon } from "@/lib/icons";
import type { Category, Debtor, Transaction } from "@/lib/types";

type SplitMode = "equal" | "fixed";
type Mode = "view" | "recategorize" | "split";

export default function TransactionDetail({
  transaction,
  onClose,
  onUpdated,
}: {
  transaction: Transaction;
  onClose: () => void;
  onUpdated: () => void;
}) {
  const [categories, setCategories] = useState<Category[] | null>(null);
  const [debtors, setDebtors] = useState<Debtor[] | null>(null);
  const [mode, setMode] = useState<Mode>("view");
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [includeMe, setIncludeMe] = useState(false);
  const [splitMode, setSplitMode] = useState<SplitMode>("equal");
  const [fixedAmounts, setFixedAmounts] = useState<Record<string, string>>({});
  const [weights, setWeights] = useState<Record<string, string>>({});
  const [myWeight, setMyWeight] = useState("1");
  const [newDebtorName, setNewDebtorName] = useState("");

  useEffect(() => {
    apiFetch<Category[]>("/api/categories")
      .then(setCategories)
      .catch(() => {});
    apiFetch<Debtor[]>("/api/debtors")
      .then(setDebtors)
      .catch(() => {});
  }, []);

  const total = Math.abs(transaction.amount);

  // "Por igual" reparte el total proporcionalmente a un multiplicador por
  // persona (por defecto 1 = reparto realmente igual); sirve para el caso
  // real de que alguien haya consumido/pagado el doble o N veces su parte.
  function weightFor(id: string): number {
    const raw = Number(weights[id]?.replace(",", "."));
    return raw > 0 ? raw : 1;
  }
  const myParsedWeight = Number(myWeight.replace(",", ".")) > 0 ? Number(myWeight.replace(",", ".")) : 1;
  const totalWeight = [...selected].reduce((sum, id) => sum + weightFor(id), 0) + (includeMe ? myParsedWeight : 0);
  function shareFor(id: string): number {
    return totalWeight > 0 ? (total * weightFor(id)) / totalWeight : 0;
  }

  const fixedAssigned = [...selected].reduce(
    (sum, id) => sum + (Number(fixedAmounts[id]?.replace(",", ".")) || 0),
    0
  );

  async function setCategory(categoryId: string) {
    setSaving(true);
    setError(null);
    try {
      await apiFetch(`/api/transactions/${transaction.entry_reference}`, {
        method: "PATCH",
        body: JSON.stringify({ category_id: categoryId }),
      });
      onUpdated();
      onClose();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo recategorizar");
    } finally {
      setSaving(false);
    }
  }

  function toggleDebtor(id: string) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  async function addDebtorInline() {
    const trimmed = newDebtorName.trim();
    if (!trimmed) return;
    try {
      const created = await apiFetch<Debtor>("/api/debtors", {
        method: "POST",
        body: JSON.stringify({ name: trimmed }),
      });
      setDebtors((prev) => [...(prev ?? []), created]);
      setSelected((prev) => new Set(prev).add(created.id));
      setNewDebtorName("");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo añadir la persona");
    }
  }

  const canSaveSplit =
    selected.size > 0 &&
    (splitMode === "equal" ? totalWeight > 0 : fixedAssigned > 0 && fixedAssigned <= total + 0.01);

  async function saveSplit() {
    setSaving(true);
    setError(null);
    try {
      const entries = [...selected].map((debtorId) => ({
        debtor_id: debtorId,
        amount: splitMode === "equal" ? shareFor(debtorId) : Number(fixedAmounts[debtorId]?.replace(",", ".")) || 0,
      }));
      await apiFetch(`/api/transactions/${transaction.entry_reference}/split`, {
        method: "POST",
        body: JSON.stringify({ entries }),
      });
      onUpdated();
      onClose();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo dividir el movimiento");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="fixed inset-0 z-30 flex flex-col bg-background">
      <div className="flex items-center justify-between border-b border-surface-border bg-surface px-4 py-3">
        <button
          onClick={mode === "view" ? onClose : () => setMode("view")}
          className="flex h-9 w-9 items-center justify-center rounded-full text-muted transition hover:bg-surface-hover"
        >
          {mode === "view" ? <X className="h-[18px] w-[18px]" /> : <ChevronLeft className="h-[18px] w-[18px]" />}
        </button>
        <h2 className="text-sm font-semibold">
          {mode === "recategorize" ? "Recategorizar" : mode === "split" ? "Dividir" : "Movimiento"}
        </h2>
        <div className="w-9" />
      </div>

      <div className="flex-1 overflow-y-auto px-4 py-5">
        {mode === "view" && (
          <>
            <div className="mb-6 flex flex-col items-center text-center">
              <span className="mb-3 flex h-14 w-14 items-center justify-center rounded-full bg-surface-hover">
                <CategoryIcon name={transaction.category?.system_icon_name ?? "help-circle"} className="h-6 w-6 text-muted" />
              </span>
              <p className="text-sm font-medium text-muted">
                {transaction.counterparty_name || transaction.remittance_information}
              </p>
              <p
                className={`tabular-nums mt-1 text-3xl font-semibold ${
                  transaction.credit_debit_indicator === "CRDT" ? "text-success" : "text-foreground"
                }`}
              >
                {transaction.credit_debit_indicator === "CRDT" ? "+" : "-"}
                {formatMoney(total, transaction.currency)}
              </p>
            </div>
            <div className="flex flex-col gap-2">
              <button
                onClick={() => setMode("recategorize")}
                className="flex items-center gap-3 rounded-2xl border border-surface-border bg-surface px-4 py-3.5 text-left text-sm font-medium shadow-[var(--shadow-card)]"
              >
                <Tag className="h-4 w-4 text-brand" />
                Recategorizar
              </button>
              <button
                onClick={() => setMode("split")}
                className="flex items-center gap-3 rounded-2xl border border-surface-border bg-surface px-4 py-3.5 text-left text-sm font-medium shadow-[var(--shadow-card)]"
              >
                <Split className="h-4 w-4 text-brand" />
                Dividir con…
              </button>
            </div>
          </>
        )}

        {mode === "recategorize" && (
          <>
            <ul className="overflow-hidden rounded-2xl border border-surface-border bg-surface shadow-[var(--shadow-card)]">
              {categories?.map((category, index) => (
                <li key={category.id} className={index > 0 ? "border-t border-surface-border" : ""}>
                  <button
                    onClick={() => setCategory(category.id)}
                    disabled={saving}
                    className="flex w-full items-center gap-3 px-4 py-3 text-left text-sm transition hover:bg-surface-hover disabled:opacity-50"
                  >
                    <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-surface-hover">
                      <CategoryIcon name={category.system_icon_name} className="h-4 w-4 text-muted" />
                    </span>
                    <span className="flex-1 font-medium">{category.name}</span>
                    {transaction.category?.id === category.id && <Check className="h-4 w-4 text-brand" />}
                  </button>
                </li>
              ))}
            </ul>
            {error && <p className="mt-3 text-sm text-danger">{error}</p>}
          </>
        )}

        {mode === "split" && (
          <div className="flex flex-col gap-4">
            <p className="text-sm text-muted">Total: {formatMoney(total, transaction.currency)}</p>

            <div className="flex items-center justify-between gap-2">
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={includeMe}
                  onChange={(e) => setIncludeMe(e.target.checked)}
                  className="h-4 w-4 accent-[var(--brand)]"
                />
                Incluirme en el reparto
              </label>
              {includeMe && splitMode === "equal" && (
                <label className="flex items-center gap-1 text-xs text-muted">
                  ×
                  <input
                    type="number"
                    inputMode="decimal"
                    min={0.1}
                    step={0.1}
                    value={myWeight}
                    onChange={(e) => setMyWeight(e.target.value)}
                    className="w-14 rounded-lg border border-surface-border bg-background px-1.5 py-1 text-right text-sm outline-none focus:border-brand"
                  />
                </label>
              )}
            </div>

            <div className="flex overflow-hidden rounded-xl border border-surface-border text-sm">
              <button
                onClick={() => setSplitMode("equal")}
                className={`flex-1 py-2 transition ${splitMode === "equal" ? "bg-brand text-brand-contrast" : "bg-surface"}`}
              >
                Por igual
              </button>
              <button
                onClick={() => setSplitMode("fixed")}
                className={`flex-1 py-2 transition ${splitMode === "fixed" ? "bg-brand text-brand-contrast" : "bg-surface"}`}
              >
                Cantidad fija
              </button>
            </div>
            {splitMode === "equal" && (
              <p className="-mt-2 text-xs text-muted">
                Reparto proporcional al multiplicador de cada persona (×1 = parte igual; ×2 = el doble).
              </p>
            )}

            <ul className="overflow-hidden rounded-2xl border border-surface-border bg-surface shadow-[var(--shadow-card)]">
              {debtors?.map((debtor, index) => (
                <li
                  key={debtor.id}
                  className={`flex items-center gap-3 px-4 py-3 ${index > 0 ? "border-t border-surface-border" : ""}`}
                >
                  <button onClick={() => toggleDebtor(debtor.id)} aria-label="Seleccionar">
                    {selected.has(debtor.id) ? (
                      <CheckCircle2 className="h-5 w-5 text-brand" />
                    ) : (
                      <Circle className="h-5 w-5 text-muted-soft" />
                    )}
                  </button>
                  <span className="flex-1 text-sm font-medium">{debtor.name}</span>
                  {selected.has(debtor.id) &&
                    (splitMode === "equal" ? (
                      <span className="flex items-center gap-2">
                        <label className="flex items-center gap-1 text-xs text-muted">
                          ×
                          <input
                            type="number"
                            inputMode="decimal"
                            min={0.1}
                            step={0.1}
                            value={weights[debtor.id] ?? "1"}
                            onChange={(e) => setWeights((prev) => ({ ...prev, [debtor.id]: e.target.value }))}
                            className="w-14 rounded-lg border border-surface-border bg-background px-1.5 py-1 text-right text-sm outline-none focus:border-brand"
                          />
                        </label>
                        <span className="tabular-nums text-sm text-muted">{formatMoney(shareFor(debtor.id), "EUR")}</span>
                      </span>
                    ) : (
                      <input
                        type="number"
                        inputMode="decimal"
                        value={fixedAmounts[debtor.id] ?? ""}
                        onChange={(e) => setFixedAmounts((prev) => ({ ...prev, [debtor.id]: e.target.value }))}
                        placeholder="0.00"
                        className="w-20 rounded-lg border border-surface-border bg-background px-2 py-1 text-right text-sm outline-none focus:border-brand"
                      />
                    ))}
                </li>
              ))}
              {debtors?.length === 0 && <li className="px-4 py-6 text-sm text-muted">Sin deudores todavía</li>}
            </ul>

            <div className="flex items-center gap-2">
              <input
                value={newDebtorName}
                onChange={(e) => setNewDebtorName(e.target.value)}
                placeholder="Añadir persona nueva"
                className="flex-1 rounded-xl border border-surface-border bg-surface px-3 py-2 text-sm outline-none focus:border-brand focus:ring-4 focus:ring-brand-soft"
              />
              <button
                onClick={addDebtorInline}
                className="rounded-xl border border-surface-border bg-surface px-3 py-2 text-sm font-medium"
              >
                Añadir
              </button>
            </div>

            {splitMode === "fixed" && (
              <p className={`text-xs ${fixedAssigned > total ? "text-danger" : "text-muted"}`}>
                Asignado: {formatMoney(fixedAssigned, "EUR")} / {formatMoney(total, "EUR")}
              </p>
            )}

            {error && <p className="text-sm text-danger">{error}</p>}

            <button
              onClick={saveSplit}
              disabled={!canSaveSplit || saving}
              className="rounded-xl bg-brand px-4 py-3 text-sm font-medium text-brand-contrast disabled:opacity-50"
            >
              Guardar
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
