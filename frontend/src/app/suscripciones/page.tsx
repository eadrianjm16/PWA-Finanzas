"use client";

import useSWR from "swr";
import { Repeat } from "lucide-react";
import AuthGuard from "@/components/AuthGuard";
import { SkeletonList } from "@/components/Skeleton";
import { apiFetch, ApiError } from "@/lib/api";
import { formatMoney, formatShortDate } from "@/lib/format";
import type { RecurringCharge } from "@/lib/types";

function SuscripcionesContent() {
  const { data: charges, error: fetchError } = useSWR<RecurringCharge[]>("/api/subscriptions", apiFetch);
  const error = fetchError
    ? fetchError instanceof ApiError
      ? fetchError.message
      : "No se pudieron cargar las suscripciones"
    : null;

  const monthlyTotal = (charges ?? [])
    .filter((c) => c.frequency === "mensual")
    .reduce((sum, c) => sum + c.amount, 0);

  return (
    <main className="mx-auto max-w-lg px-4 pb-28 pt-6">
      <h1 className="mb-1 text-2xl font-semibold tracking-tight">Suscripciones</h1>
      <p className="mb-6 text-sm text-muted">Cargos que se repiten, detectados a partir de tu historial</p>

      {error && <p className="mb-4 text-sm text-danger">{error}</p>}
      {!charges && <SkeletonList rows={4} />}

      {charges?.length === 0 && (
        <div className="flex flex-col items-center rounded-2xl border border-dashed border-surface-border px-6 py-10 text-center">
          <p className="text-sm text-muted">
            Todavía no hemos detectado ningún cargo recurrente. Hace falta al menos dos cobros del mismo comercio
            con una cadencia mensual o anual.
          </p>
        </div>
      )}

      {charges && charges.length > 0 && (
        <>
          <div className="mb-4 rounded-2xl border border-surface-border bg-surface px-4 py-3.5 shadow-[var(--shadow-card)]">
            <p className="text-xs text-muted">Total mensual estimado</p>
            <p className="text-xl font-semibold tracking-tight">{formatMoney(monthlyTotal, "EUR")}</p>
          </div>

          <ul className="flex flex-col gap-2">
            {charges.map((charge) => (
              <li
                key={charge.id}
                className="flex items-center gap-3 rounded-2xl border border-surface-border bg-surface px-4 py-3.5 shadow-[var(--shadow-card)]"
              >
                <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-brand-soft">
                  <Repeat className="h-4 w-4 text-brand" />
                </span>
                <div className="flex-1">
                  <p className="text-sm font-medium">{charge.name}</p>
                  <p className="text-xs text-muted">
                    {charge.frequency === "mensual" ? "Mensual" : "Anual"} · próximo cobro ~{" "}
                    {formatShortDate(charge.next_expected_date)}
                  </p>
                </div>
                <p className="text-sm font-semibold">{formatMoney(charge.amount, charge.currency)}</p>
              </li>
            ))}
          </ul>
        </>
      )}
    </main>
  );
}

export default function SuscripcionesPage() {
  return (
    <AuthGuard>
      <SuscripcionesContent />
    </AuthGuard>
  );
}
