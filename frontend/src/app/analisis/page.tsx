"use client";

import { useState } from "react";
import useSWR from "swr";
import AuthGuard from "@/components/AuthGuard";
import BarChart from "@/components/BarChart";
import CategoryDetail from "@/components/CategoryDetail";
import DonutChart from "@/components/DonutChart";
import { apiFetch, ApiError } from "@/lib/api";
import { formatMoney, formatMonthLabel, shiftMonth } from "@/lib/format";
import type { AnalysisSummary } from "@/lib/types";

const PALETTE = ["#2563eb", "#16a34a", "#d97706", "#dc2626", "#7c3aed", "#0891b2", "#db2777", "#65a30d"];

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

  const monthKey = `${year}-${String(month).padStart(2, "0")}`;

  function goToMonth(delta: number) {
    const next = shiftMonth(monthKey, delta);
    setYear(next.year);
    setMonth(next.month);
  }

  return (
    <main className="mx-auto max-w-lg px-4 pb-24 pt-6">
      <h1 className="mb-4 text-xl font-semibold">Análisis</h1>

      <div className="mb-6 flex items-center justify-between">
        <button onClick={() => goToMonth(-1)} className="px-2 py-1 text-lg text-neutral-500" aria-label="Mes anterior">
          ‹
        </button>
        <span className="text-sm font-medium capitalize">{formatMonthLabel(monthKey)}</span>
        <button onClick={() => goToMonth(1)} className="px-2 py-1 text-lg text-neutral-500" aria-label="Mes siguiente">
          ›
        </button>
      </div>

      {error && <p className="mb-4 text-sm text-red-600">{error}</p>}
      {!summary && !error && <p className="text-sm text-neutral-500">Cargando…</p>}

      {summary && (
        <>
          <div className="mb-6 grid grid-cols-3 gap-2 text-center">
            <div>
              <p className="text-xs text-neutral-500">Ingresos</p>
              <p className="text-sm font-semibold text-emerald-600">{formatMoney(summary.income, "EUR")}</p>
            </div>
            <div>
              <p className="text-xs text-neutral-500">Gastos</p>
              <p className="text-sm font-semibold">{formatMoney(summary.expense, "EUR")}</p>
            </div>
            <div>
              <p className="text-xs text-neutral-500">Neto</p>
              <p className={`text-sm font-semibold ${summary.net >= 0 ? "text-emerald-600" : "text-red-600"}`}>
                {formatMoney(summary.net, "EUR")}
              </p>
            </div>
          </div>

          {summary.no_computable > 0 && (
            <p className="mb-6 text-center text-xs text-neutral-500">
              + {formatMoney(summary.no_computable, "EUR")} en traspasos entre tus cuentas (no computable)
            </p>
          )}

          {summary.budget_used_ratio != null && (
            <div className="mb-8">
              <p className="mb-1 text-xs text-neutral-500">
                {Math.round(summary.budget_used_ratio * 100)}% del presupuesto previsto
              </p>
              <div className="h-1.5 w-full overflow-hidden rounded-full bg-neutral-100 dark:bg-neutral-800">
                <div
                  className={`h-full rounded-full ${
                    summary.budget_used_ratio > 1 ? "bg-red-500" : "bg-neutral-900 dark:bg-white"
                  }`}
                  style={{ width: `${Math.min(summary.budget_used_ratio, 1) * 100}%` }}
                />
              </div>
            </div>
          )}

          <section className="mb-8">
            <h2 className="mb-3 text-sm font-medium text-neutral-500">Últimos 6 meses</h2>
            <BarChart data={summary.last_six_months} />
          </section>

          <section>
            <h2 className="mb-3 text-sm font-medium text-neutral-500">Gastos por categoría</h2>
            {summary.category_breakdown.length === 0 ? (
              <p className="text-sm text-neutral-500">Sin gastos categorizados este mes.</p>
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
