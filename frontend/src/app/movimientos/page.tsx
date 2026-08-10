"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import AuthGuard from "@/components/AuthGuard";
import TransactionDetail from "@/components/TransactionDetail";
import { apiFetch, ApiError } from "@/lib/api";
import { dayKey, formatDay, formatMoney } from "@/lib/format";
import type { SyncResult, Transaction } from "@/lib/types";

function MovimientosContent() {
  const [transactions, setTransactions] = useState<Transaction[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [syncing, setSyncing] = useState(false);
  const [selected, setSelected] = useState<Transaction | null>(null);

  const load = useCallback(async () => {
    try {
      const data = await apiFetch<Transaction[]>("/api/transactions?limit=200");
      setTransactions(data);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudieron cargar los movimientos");
    }
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    load();
  }, [load]);

  async function sync() {
    setSyncing(true);
    setError(null);
    try {
      const results = await apiFetch<SyncResult[]>("/api/transactions/sync", { method: "POST" });
      const failed = results.filter((r) => !r.ok);
      if (failed.length > 0) {
        setError(`No se pudo sincronizar ${failed.length} cuenta(s).`);
      }
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo sincronizar");
    } finally {
      setSyncing(false);
    }
  }

  const groups = useMemo(() => {
    if (!transactions) return [];
    const byDay = new Map<string, Transaction[]>();
    for (const tx of transactions) {
      const key = dayKey(tx.booking_date);
      if (!byDay.has(key)) byDay.set(key, []);
      byDay.get(key)!.push(tx);
    }
    return Array.from(byDay.entries()).sort((a, b) => (a[0] < b[0] ? 1 : -1));
  }, [transactions]);

  return (
    <main className="mx-auto max-w-lg px-4 pb-24 pt-6">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-xl font-semibold">Movimientos</h1>
        <button
          onClick={sync}
          disabled={syncing}
          className="rounded-full bg-neutral-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-50 dark:bg-white dark:text-neutral-900"
        >
          {syncing ? "Sincronizando…" : "Sincronizar"}
        </button>
      </div>

      {error && <p className="mb-4 text-sm text-red-600">{error}</p>}

      {transactions === null && <p className="text-sm text-neutral-500">Cargando…</p>}
      {transactions?.length === 0 && (
        <p className="text-sm text-neutral-500">
          Sin movimientos todavía. Conecta un banco y pulsa &quot;Sincronizar&quot;.
        </p>
      )}

      <div className="flex flex-col gap-6">
        {groups.map(([day, dayTransactions]) => (
          <section key={day}>
            <h2 className="mb-2 text-xs font-medium tracking-wide text-neutral-500">{formatDay(day)}</h2>
            <ul className="divide-y divide-neutral-100 overflow-hidden rounded-xl border border-neutral-200 dark:divide-neutral-800 dark:border-neutral-800">
              {dayTransactions.map((tx) => {
                const isCredit = tx.credit_debit_indicator === "CRDT";
                const title = tx.counterparty_name || tx.remittance_information || "Movimiento";
                return (
                  <li key={tx.entry_reference}>
                    <button
                      onClick={() => setSelected(tx)}
                      className="flex w-full items-center justify-between px-4 py-3 text-left"
                    >
                      <div className="min-w-0 pr-3">
                        <p className="truncate text-sm font-medium">{title}</p>
                        <div className="flex items-center gap-2">
                          {tx.category && <p className="text-xs text-neutral-500">{tx.category.name}</p>}
                          {tx.has_debt_entries && (
                            <span className="rounded-full bg-blue-100 px-2 py-0.5 text-[10px] font-semibold text-blue-700 dark:bg-blue-950 dark:text-blue-300">
                              Dividido
                            </span>
                          )}
                        </div>
                      </div>
                      <span
                        className={`shrink-0 text-sm font-medium ${isCredit ? "text-emerald-600" : "text-neutral-900 dark:text-neutral-100"}`}
                      >
                        {isCredit ? "+" : "-"}
                        {formatMoney(Math.abs(tx.amount), tx.currency)}
                      </span>
                    </button>
                  </li>
                );
              })}
            </ul>
          </section>
        ))}
      </div>

      {selected && (
        <TransactionDetail
          transaction={selected}
          onClose={() => setSelected(null)}
          onUpdated={load}
        />
      )}
    </main>
  );
}

export default function MovimientosPage() {
  return (
    <AuthGuard>
      <MovimientosContent />
    </AuthGuard>
  );
}
