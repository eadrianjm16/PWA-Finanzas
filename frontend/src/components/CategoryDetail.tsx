"use client";

import { useEffect, useState } from "react";
import { X } from "lucide-react";
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
    <div className="fixed inset-0 z-20 flex flex-col bg-background">
      <div className="flex items-center justify-between border-b border-surface-border bg-surface px-4 py-3">
        <div>
          <h2 className="text-sm font-semibold">{categoryName}</h2>
          {transactions && <p className="tabular-nums text-xs text-muted">{formatMoney(total, "EUR")}</p>}
        </div>
        <button
          onClick={onClose}
          className="flex h-9 w-9 items-center justify-center rounded-full text-muted transition hover:bg-surface-hover"
          aria-label="Cerrar"
        >
          <X className="h-[18px] w-[18px]" />
        </button>
      </div>

      {error && <p className="px-4 pt-3 text-sm text-danger">{error}</p>}

      <div className="flex-1 overflow-y-auto px-4 py-3">
        {transactions === null && <p className="px-1 py-6 text-sm text-muted">Cargando…</p>}
        <ul className="overflow-hidden rounded-2xl border border-surface-border bg-surface shadow-[var(--shadow-card)]">
          {transactions?.map((tx, index) => (
            <li
              key={tx.entry_reference}
              className={`flex items-center justify-between px-4 py-3.5 ${index > 0 ? "border-t border-surface-border" : ""}`}
            >
              <span className="truncate pr-3 text-sm font-medium">
                {tx.counterparty_name || tx.remittance_information || "Movimiento"}
              </span>
              <span className="tabular-nums shrink-0 text-sm font-semibold">
                {formatMoney(Math.abs(tx.amount), tx.currency)}
              </span>
            </li>
          ))}
          {transactions?.length === 0 && <li className="px-4 py-6 text-sm text-muted">Sin movimientos este mes.</li>}
        </ul>
      </div>
    </div>
  );
}
