"use client";

import { useEffect, useState } from "react";
import { apiFetch, ApiError } from "@/lib/api";
import { formatMoney } from "@/lib/format";
import type { Transaction } from "@/lib/types";

function monthRange(year: number, month: number): { from: string; to: string } {
  const from = new Date(Date.UTC(year, month - 1, 1)).toISOString();
  const to = new Date(Date.UTC(year, month, 0, 23, 59, 59)).toISOString();
  return { from, to };
}

export default function CategoryDetail({
  categoryId,
  categoryName,
  year,
  month,
  onClose,
}: {
  categoryId: string;
  categoryName: string;
  year: number;
  month: number;
  onClose: () => void;
}) {
  const [transactions, setTransactions] = useState<Transaction[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const { from, to } = monthRange(year, month);
    apiFetch<Transaction[]>(
      `/api/transactions?category_id=${categoryId}&date_from=${encodeURIComponent(from)}&date_to=${encodeURIComponent(to)}&limit=200`
    )
      .then(setTransactions)
      .catch((err) => setError(err instanceof ApiError ? err.message : "No se pudieron cargar los movimientos"));
  }, [categoryId, year, month]);

  const total = (transactions ?? []).reduce((sum, tx) => sum + Math.abs(tx.amount), 0);

  return (
    <div className="fixed inset-0 z-20 flex flex-col bg-white dark:bg-neutral-950">
      <div className="flex items-center justify-between border-b border-neutral-200 px-4 py-3 dark:border-neutral-800">
        <div>
          <h2 className="text-sm font-semibold">{categoryName}</h2>
          {transactions && <p className="text-xs text-neutral-500">{formatMoney(total, "EUR")}</p>}
        </div>
        <button onClick={onClose} className="text-sm text-neutral-500">
          Cerrar
        </button>
      </div>

      {error && <p className="px-4 pt-3 text-sm text-red-600">{error}</p>}

      <div className="flex-1 overflow-y-auto">
        {transactions === null && <p className="px-4 py-6 text-sm text-neutral-500">Cargando…</p>}
        <ul className="divide-y divide-neutral-100 dark:divide-neutral-900">
          {transactions?.map((tx) => (
            <li key={tx.entry_reference} className="flex items-center justify-between px-4 py-3">
              <span className="truncate pr-3 text-sm">
                {tx.counterparty_name || tx.remittance_information || "Movimiento"}
              </span>
              <span className="shrink-0 text-sm font-medium">{formatMoney(Math.abs(tx.amount), tx.currency)}</span>
            </li>
          ))}
          {transactions?.length === 0 && (
            <li className="px-4 py-6 text-sm text-neutral-500">Sin movimientos este mes.</li>
          )}
        </ul>
      </div>
    </div>
  );
}
