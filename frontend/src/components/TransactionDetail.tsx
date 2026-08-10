"use client";

import { useEffect, useState } from "react";
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
  const divisor = selected.size + (includeMe ? 1 : 0);
  const equalShare = divisor > 0 ? total / divisor : 0;
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
    (splitMode === "equal" ? divisor > 0 : fixedAssigned > 0 && fixedAssigned <= total + 0.01);

  async function saveSplit() {
    setSaving(true);
    setError(null);
    try {
      const entries = [...selected].map((debtorId) => ({
        debtor_id: debtorId,
        amount: splitMode === "equal" ? equalShare : Number(fixedAmounts[debtorId]?.replace(",", ".")) || 0,
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
    <div className="fixed inset-0 z-30 flex flex-col bg-white dark:bg-neutral-950">
      <div className="flex items-center justify-between border-b border-neutral-200 px-4 py-3 dark:border-neutral-800">
        <button onClick={mode === "view" ? onClose : () => setMode("view")} className="text-sm text-neutral-500">
          {mode === "view" ? "Cerrar" : "‹ Atrás"}
        </button>
        <h2 className="text-sm font-semibold">
          {mode === "recategorize" ? "Recategorizar" : mode === "split" ? "Dividir" : "Movimiento"}
        </h2>
        <div className="w-12" />
      </div>

      <div className="flex-1 overflow-y-auto px-4 py-4">
        {mode === "view" && (
          <>
            <p className="text-sm font-medium">{transaction.counterparty_name || transaction.remittance_information}</p>
            <p className="mb-6 text-2xl font-semibold">
              {transaction.credit_debit_indicator === "CRDT" ? "+" : "-"}
              {formatMoney(total, transaction.currency)}
            </p>
            <div className="flex flex-col gap-2">
              <button
                onClick={() => setMode("recategorize")}
                className="rounded-xl border border-neutral-200 px-4 py-3 text-left text-sm font-medium dark:border-neutral-800"
              >
                Recategorizar
              </button>
              <button
                onClick={() => setMode("split")}
                className="rounded-xl border border-neutral-200 px-4 py-3 text-left text-sm font-medium dark:border-neutral-800"
              >
                Dividir con…
              </button>
            </div>
          </>
        )}

        {mode === "recategorize" && (
          <>
            <ul className="divide-y divide-neutral-100 overflow-hidden rounded-xl border border-neutral-200 dark:divide-neutral-800 dark:border-neutral-800">
              {categories?.map((category) => (
                <li key={category.id}>
                  <button
                    onClick={() => setCategory(category.id)}
                    disabled={saving}
                    className="flex w-full items-center gap-3 px-4 py-3 text-left text-sm disabled:opacity-50"
                  >
                    <CategoryIcon name={category.system_icon_name} className="h-4 w-4 text-neutral-500" />
                    <span className="flex-1">{category.name}</span>
                    {transaction.category?.id === category.id && <span className="text-neutral-400">✓</span>}
                  </button>
                </li>
              ))}
            </ul>
            {error && <p className="mt-3 text-sm text-red-600">{error}</p>}
          </>
        )}

        {mode === "split" && (
          <div className="flex flex-col gap-4">
            <p className="text-sm text-neutral-500">Total: {formatMoney(total, transaction.currency)}</p>

            <label className="flex items-center gap-2 text-sm">
              <input type="checkbox" checked={includeMe} onChange={(e) => setIncludeMe(e.target.checked)} />
              Incluirme en el reparto
            </label>

            <div className="flex overflow-hidden rounded-lg border border-neutral-300 text-sm dark:border-neutral-700">
              <button
                onClick={() => setSplitMode("equal")}
                className={`flex-1 py-2 ${splitMode === "equal" ? "bg-neutral-900 text-white dark:bg-white dark:text-neutral-900" : ""}`}
              >
                Por igual
              </button>
              <button
                onClick={() => setSplitMode("fixed")}
                className={`flex-1 py-2 ${splitMode === "fixed" ? "bg-neutral-900 text-white dark:bg-white dark:text-neutral-900" : ""}`}
              >
                Cantidad fija
              </button>
            </div>

            <ul className="divide-y divide-neutral-100 overflow-hidden rounded-xl border border-neutral-200 dark:divide-neutral-800 dark:border-neutral-800">
              {debtors?.map((debtor) => (
                <li key={debtor.id} className="flex items-center gap-3 px-4 py-3">
                  <button onClick={() => toggleDebtor(debtor.id)} className="text-lg leading-none" aria-label="Seleccionar">
                    {selected.has(debtor.id) ? "●" : "○"}
                  </button>
                  <span className="flex-1 text-sm">{debtor.name}</span>
                  {selected.has(debtor.id) &&
                    (splitMode === "equal" ? (
                      <span className="text-sm text-neutral-500">{formatMoney(equalShare, "EUR")}</span>
                    ) : (
                      <input
                        type="number"
                        inputMode="decimal"
                        value={fixedAmounts[debtor.id] ?? ""}
                        onChange={(e) => setFixedAmounts((prev) => ({ ...prev, [debtor.id]: e.target.value }))}
                        placeholder="0.00"
                        className="w-20 rounded-lg border border-neutral-300 px-2 py-1 text-right text-sm outline-none dark:border-neutral-700 dark:bg-neutral-900"
                      />
                    ))}
                </li>
              ))}
              {debtors?.length === 0 && <li className="px-4 py-6 text-sm text-neutral-500">Sin deudores todavía</li>}
            </ul>

            <div className="flex items-center gap-2">
              <input
                value={newDebtorName}
                onChange={(e) => setNewDebtorName(e.target.value)}
                placeholder="Añadir persona nueva"
                className="flex-1 rounded-lg border border-neutral-300 px-3 py-2 text-sm outline-none dark:border-neutral-700 dark:bg-neutral-900"
              />
              <button
                onClick={addDebtorInline}
                className="rounded-lg border border-neutral-300 px-3 py-2 text-sm dark:border-neutral-700"
              >
                Añadir
              </button>
            </div>

            {splitMode === "fixed" && (
              <p className={`text-xs ${fixedAssigned > total ? "text-red-600" : "text-neutral-500"}`}>
                Asignado: {formatMoney(fixedAssigned, "EUR")} / {formatMoney(total, "EUR")}
              </p>
            )}

            {error && <p className="text-sm text-red-600">{error}</p>}

            <button
              onClick={saveSplit}
              disabled={!canSaveSplit || saving}
              className="rounded-xl bg-neutral-900 px-4 py-3 text-sm font-medium text-white disabled:opacity-50 dark:bg-white dark:text-neutral-900"
            >
              Guardar
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
