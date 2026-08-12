"use client";

import { useState } from "react";
import useSWR from "swr";
import { ChevronLeft, ChevronRight } from "lucide-react";
import AuthGuard from "@/components/AuthGuard";
import BarChart from "@/components/BarChart";
import CategoryDetail from "@/components/CategoryDetail";
import DonutChart from "@/components/DonutChart";
import LineChart from "@/components/LineChart";
import { Skeleton } from "@/components/Skeleton";
import { apiFetch, ApiError } from "@/lib/api";
import { formatMoney, formatMonthLabel, shiftMonth } from "@/lib/format";
import type { AnalysisSummary, NetWorthPoint } from "@/lib/types";

const PALETTE = ["#5b5ff2", "#0ea968", "#d98c1a", "#e64c53", "#0891b2", "#a855f7", "#db2777", "#65a30d"];

function AnalisisContent() {
  const now = new Date();
  const [year, setYear] = useState(now.getFullYear());
  const [month, setMonth] = useState(now.getMonth() + 1);
  const [selectedCategory, setSelectedCategory] = useState<{ id: string; name: string } | null>(null);

  const { data: summary, error: fetchError } = useSWR<AnalysisSummary>(
    `/api/analysis/summary?year=${year}&month=${month}`,
    apiFetch
  );
  const error = fetchError ? (fetchError instanceof ApiError ? fetchError.message : "No se pudo cargar el análisis") : null;
  const { data: netWorthHistory } = useSWR<NetWorthPoint[]>("/api/net-worth/history", apiFetch);

  const monthKey = `${year}-${String(month).padStart(2, "0")}`;
  const currentMonthKey = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
  const isCurrentMonth = monthKey === currentMonthKey;

  function goToMonth(delta: number) {
    const next = shiftMonth(monthKey, delta);
    setYear(next.year);
    setMonth(next.month);
  }

  return (
    <main className="mx-auto max-w-lg px-4 pb-28 pt-6">
      <h1 className="mb-4 text-2xl font-semibold tracking-tight">Análisis</h1>

      <div className="mb-6 flex items-center justify-between rounded-2xl border border-surface-border bg-surface px-2 py-1.5 shadow-[var(--shadow-card)]">
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

      {error && <p className="mb-4 text-sm text-danger">{error}</p>}
      {!summary && !error && (
        <div className="flex flex-col gap-4">
          <Skeleton className="h-24 w-full" />
          <Skeleton className="h-40 w-full" />
          <Skeleton className="h-48 w-full" />
        </div>
      )}

      {summary && (
        <>
          <div className="mb-6 grid grid-cols-3 gap-2">
            <div className="rounded-2xl border border-surface-border bg-surface p-3 text-center shadow-[var(--shadow-card)]">
              <p className="mb-0.5 text-[11px] font-medium text-muted">Ingresos</p>
              <p className="tabular-nums text-sm font-semibold text-success">{formatMoney(summary.income, "EUR")}</p>
            </div>
            <div className="rounded-2xl border border-surface-border bg-surface p-3 text-center shadow-[var(--shadow-card)]">
              <p className="mb-0.5 text-[11px] font-medium text-muted">Gastos</p>
              <p className="tabular-nums text-sm font-semibold">{formatMoney(summary.expense, "EUR")}</p>
            </div>
            <div className="rounded-2xl border border-surface-border bg-surface p-3 text-center shadow-[var(--shadow-card)]">
              <p className="mb-0.5 text-[11px] font-medium text-muted">Neto</p>
              <p className={`tabular-nums text-sm font-semibold ${summary.net >= 0 ? "text-success" : "text-danger"}`}>
                {formatMoney(summary.net, "EUR")}
              </p>
            </div>
          </div>

          {summary.no_computable > 0 && (
            <p className="mb-6 text-center text-xs text-muted">
              + {formatMoney(summary.no_computable, "EUR")} en traspasos entre tus cuentas (no computable)
            </p>
          )}

          {summary.budget_used_ratio != null && (
            <div className="mb-8 rounded-2xl border border-surface-border bg-surface p-4 shadow-[var(--shadow-card)]">
              <p className="mb-2 text-xs font-medium text-muted">
                {Math.round(summary.budget_used_ratio * 100)}% del presupuesto previsto
              </p>
              <div className="h-2 w-full overflow-hidden rounded-full bg-surface-hover">
                <div
                  className={`h-full rounded-full transition-all ${
                    summary.budget_used_ratio > 1 ? "bg-danger" : "bg-brand"
                  }`}
                  style={{ width: `${Math.min(summary.budget_used_ratio, 1) * 100}%` }}
                />
              </div>
            </div>
          )}

          <section className="mb-6 rounded-2xl border border-surface-border bg-surface p-4 shadow-[var(--shadow-card)]">
            <h2 className="mb-4 text-sm font-semibold text-muted">Últimos 6 meses</h2>
            <BarChart data={summary.last_six_months} />
          </section>

          {netWorthHistory && netWorthHistory.length > 0 && (
            <section className="mb-6 rounded-2xl border border-surface-border bg-surface p-4 shadow-[var(--shadow-card)]">
              <div className="mb-4 flex items-center justify-between">
                <h2 className="text-sm font-semibold text-muted">Patrimonio neto</h2>
                <p className="tabular-nums text-sm font-semibold">
                  {formatMoney(netWorthHistory[netWorthHistory.length - 1].total_amount, "EUR")}
                </p>
              </div>
              <LineChart points={netWorthHistory.map((p) => ({ date: p.date, value: p.total_amount }))} />
            </section>
          )}

          <section className="mb-6 rounded-2xl border border-surface-border bg-surface p-4 shadow-[var(--shadow-card)]">
            <h2 className="mb-4 text-sm font-semibold text-muted">Gastos por categoría</h2>
            {summary.category_breakdown.length === 0 ? (
              <p className="text-sm text-muted">Sin gastos categorizados este mes.</p>
            ) : (
              <DonutChart
                segments={summary.category_breakdown.map((item, index) => ({
                  id: item.category.id,
                  label: item.category.name,
                  value: item.spent,
                  color: PALETTE[index % PALETTE.length],
                }))}
                onSelect={(id) => {
                  const item = summary.category_breakdown.find((b) => b.category.id === id);
                  if (item) setSelectedCategory({ id, name: item.category.name });
                }}
              />
            )}
          </section>

          <section className="rounded-2xl border border-surface-border bg-surface p-4 shadow-[var(--shadow-card)]">
            <h2 className="mb-4 text-sm font-semibold text-muted">Ingresos por categoría</h2>
            {(summary.income_breakdown ?? []).length === 0 ? (
              <p className="text-sm text-muted">Sin ingresos categorizados este mes.</p>
            ) : (
              <DonutChart
                segments={(summary.income_breakdown ?? []).map((item, index) => ({
                  id: item.category.id,
                  label: item.category.name,
                  value: item.spent,
                  color: PALETTE[index % PALETTE.length],
                }))}
                onSelect={(id) => {
                  const item = (summary.income_breakdown ?? []).find((b) => b.category.id === id);
                  if (item) setSelectedCategory({ id, name: item.category.name });
                }}
              />
            )}
          </section>
        </>
      )}

      {selectedCategory && (
        <CategoryDetail
          categoryId={selectedCategory.id}
          categoryName={selectedCategory.name}
          year={year}
          month={month}
          onClose={() => setSelectedCategory(null)}
        />
      )}
    </main>
  );
}

export default function AnalisisPage() {
  return (
    <AuthGuard>
      <AnalisisContent />
    </AuthGuard>
  );
}
