"use client";

import { useEffect, useMemo, useState } from "react";
import useSWR from "swr";
import { ArrowDownLeft, ChevronLeft, ChevronRight, Download, RefreshCw, Search, Split, X } from "lucide-react";
import AuthGuard from "@/components/AuthGuard";
import { SkeletonList } from "@/components/Skeleton";
import TransactionDetail from "@/components/TransactionDetail";
import { CategoryIcon } from "@/lib/icons";
import { apiFetch, ApiError, downloadFile } from "@/lib/api";
import { dayKey, formatDay, formatMoney, formatMonthLabel, shiftMonth } from "@/lib/format";
import type { SyncResult, Transaction } from "@/lib/types";

function monthBounds(year: number, month: number): { dateFrom: string; dateTo: string } {
  const from = new Date(Date.UTC(year, month - 1, 1, 0, 0, 0));
  const to = new Date(Date.UTC(year, month, 0, 23, 59, 59));
  return { dateFrom: from.toISOString(), dateTo: to.toISOString() };
}

function MovimientosContent() {
  const now = new Date();
  const [year, setYear] = useState(now.getFullYear());
  const [month, setMonth] = useState(now.getMonth() + 1);
  const monthKey = `${year}-${String(month).padStart(2, "0")}`;
  const currentMonthKey = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
  const isCurrentMonth = monthKey === currentMonthKey;

  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");

  useEffect(() => {
    const timer = setTimeout(() => setSearch(searchInput.trim()), 300);
    return () => clearTimeout(timer);
  }, [searchInput]);

  function goToMonth(delta: number) {
    const next = shiftMonth(monthKey, delta);
    setYear(next.year);
    setMonth(next.month);
  }

  const { dateFrom, dateTo } = monthBounds(year, month);
  const filterParams = `date_from=${dateFrom}&date_to=${dateTo}${search ? `&search=${encodeURIComponent(search)}` : ""}`;
  const { data: transactions, mutate } = useSWR<Transaction[]>(
    `/api/transactions?limit=500&${filterParams}`,
    apiFetch
  );
  const [error, setError] = useState<string | null>(null);
  const [syncing, setSyncing] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [selected, setSelected] = useState<Transaction | null>(null);

  async function sync() {
    setSyncing(true);
    setError(null);
    try {
      const results = await apiFetch<SyncResult[]>("/api/transactions/sync", { method: "POST" });
      const failed = results.filter((r) => !r.ok);
      if (failed.length > 0) {
        setError(`No se pudo sincronizar ${failed.length} cuenta(s).`);
      }
      await mutate();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo sincronizar");
    } finally {
      setSyncing(false);
    }
  }

  async function exportCsv() {
    setExporting(true);
    setError(null);
    try {
      await downloadFile(`/api/transactions/export?${filterParams}`, `movimientos-${monthKey}.csv`);
    } catch {
      setError("No se pudo exportar");
    } finally {
      setExporting(false);
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
    <main className="mx-auto max-w-lg px-4 pb-28 pt-6">
      <div className="mb-4 flex items-center justify-between">
        <h1 className="text-2xl font-semibold tracking-tight">Movimientos</h1>
        <button
          onClick={sync}
          disabled={syncing}
          className="flex items-center gap-1.5 rounded-full bg-brand px-4 py-2 text-sm font-medium text-brand-contrast shadow-[var(--shadow-card)] transition active:scale-95 disabled:opacity-50"
        >
          <RefreshCw className={`h-4 w-4 ${syncing ? "animate-spin" : ""}`} strokeWidth={2.5} />
          {syncing ? "Sincronizando" : "Sincronizar"}
        </button>
      </div>

      <div className="mb-4 flex items-center justify-between rounded-2xl border border-surface-border bg-surface px-2 py-1.5 shadow-[var(--shadow-card)]">
        <button
          onClick={() => goToMonth(-1)}
          className="flex h-9 w-9 items-center justify-center rounded-full text-muted transition hover:bg-surface-hover"
          aria-label="Mes anterior"
        >
          <ChevronLeft className="h-4 w-4" />
        </button>
        <span className="text-sm font-semibold">{formatMonthLabel(monthKey)}</span>
        <button
          onClick={() => goToMonth(1)}
          disabled={isCurrentMonth}
          className="flex h-9 w-9 items-center justify-center rounded-full text-muted transition hover:bg-surface-hover disabled:opacity-30"
          aria-label="Mes siguiente"
        >
          <ChevronRight className="h-4 w-4" />
        </button>
      </div>

      <div className="mb-4 flex gap-2">
        <div className="relative flex-1">
          <Search className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-soft" />
          <input
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            placeholder="Buscar movimiento…"
            className="w-full rounded-xl border border-surface-border bg-surface py-2.5 pl-10 pr-9 text-sm outline-none transition-colors focus:border-brand focus:ring-4 focus:ring-brand-soft"
          />
          {searchInput && (
            <button
              onClick={() => setSearchInput("")}
              aria-label="Borrar búsqueda"
              className="absolute right-2.5 top-1/2 flex h-6 w-6 -translate-y-1/2 items-center justify-center rounded-full text-muted-soft hover:bg-surface-hover"
            >
              <X className="h-3.5 w-3.5" />
            </button>
          )}
        </div>
        <button
          onClick={exportCsv}
          disabled={exporting || !transactions?.length}
          aria-label="Exportar CSV"
          className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl border border-surface-border bg-surface text-muted shadow-[var(--shadow-card)] transition hover:bg-surface-hover disabled:opacity-50"
        >
          <Download className="h-4 w-4" />
        </button>
      </div>

      {error && <p className="mb-4 text-sm text-danger">{error}</p>}

      {!transactions && <SkeletonList rows={6} />}
      {transactions?.length === 0 && search && (
        <div className="flex flex-col items-center rounded-2xl border border-dashed border-surface-border px-6 py-10 text-center">
          <p className="text-sm text-muted">Sin resultados para &quot;{search}&quot;.</p>
        </div>
      )}
      {transactions?.length === 0 && !search && (
        <div className="flex flex-col items-center rounded-2xl border border-dashed border-surface-border px-6 py-10 text-center">
          <span className="mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-brand-soft">
            <ArrowDownLeft className="h-6 w-6 text-brand" />
          </span>
          <p className="text-sm text-muted">Sin movimientos este mes.</p>
          <p className="text-sm text-muted">Conecta un banco y pulsa &quot;Sincronizar&quot;.</p>
        </div>
      )}

      <div className="flex flex-col gap-6">
        {groups.map(([day, dayTransactions]) => (
          <section key={day}>
            <h2 className="mb-2 px-1 text-xs font-semibold uppercase tracking-wide text-muted-soft">
              {formatDay(day)}
            </h2>
            <ul className="overflow-hidden rounded-2xl border border-surface-border bg-surface shadow-[var(--shadow-card)]">
              {dayTransactions.map((tx, index) => {
                const isCredit = tx.credit_debit_indicator === "CRDT";
                const title = tx.counterparty_name || tx.remittance_information || "Movimiento";
                return (
                  <li key={tx.entry_reference} className={index > 0 ? "border-t border-surface-border" : ""}>
                    <button
                      onClick={() => setSelected(tx)}
                      className="flex w-full items-center gap-3 px-4 py-3.5 text-left transition hover:bg-surface-hover"
                    >
                      <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-surface-hover">
                        <CategoryIcon
                          name={tx.category?.system_icon_name ?? "help-circle"}
                          className="h-[18px] w-[18px] text-muted"
                        />
                      </span>
                      <div className="min-w-0 flex-1 pr-3">
                        <p className="truncate text-sm font-medium">{title}</p>
                        <div className="flex items-center gap-1.5">
                          {tx.category && <p className="truncate text-xs text-muted">{tx.category.name}</p>}
                          {tx.has_debt_entries && (
                            <span className="flex items-center gap-0.5 rounded-full bg-brand-soft px-1.5 py-0.5 text-[10px] font-semibold text-brand">
                              <Split className="h-2.5 w-2.5" />
                              Dividido
                            </span>
                          )}
                        </div>
                      </div>
                      <span
                        className={`tabular-nums shrink-0 text-sm font-semibold ${isCredit ? "text-success" : "text-foreground"}`}
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

      {selected && <TransactionDetail transaction={selected} onClose={() => setSelected(null)} onUpdated={mutate} />}
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
