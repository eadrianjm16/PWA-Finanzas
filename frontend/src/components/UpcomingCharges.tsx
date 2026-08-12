"use client";

import Link from "next/link";
import useSWR from "swr";
import { Repeat } from "lucide-react";
import { apiFetch } from "@/lib/api";
import { formatMoney, formatShortDate } from "@/lib/format";
import type { RecurringCharge } from "@/lib/types";

const FORECAST_WINDOW_DAYS = 14;

export default function UpcomingCharges() {
  const { data: charges } = useSWR<RecurringCharge[]>("/api/subscriptions", apiFetch);

  const now = new Date().getTime();
  const upcoming = (charges ?? []).filter((charge) => {
    const daysUntil = (new Date(charge.next_expected_date).getTime() - now) / 86_400_000;
    return daysUntil <= FORECAST_WINDOW_DAYS;
  });

  if (upcoming.length === 0) return null;

  return (
    <Link
      href="/suscripciones"
      className="mb-6 block overflow-hidden rounded-2xl border border-surface-border bg-surface shadow-[var(--shadow-card)]"
    >
      <p className="px-4 pt-3.5 text-xs font-medium text-muted">Próximos cargos previstos</p>
      <ul>
        {upcoming.slice(0, 3).map((charge, index) => (
          <li
            key={charge.id}
            className={`flex items-center gap-3 px-4 py-3 ${index > 0 ? "border-t border-surface-border" : ""}`}
          >
            <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-brand-soft">
              <Repeat className="h-3.5 w-3.5 text-brand" />
            </span>
            <div className="flex-1">
              <p className="text-sm font-medium">{charge.name}</p>
              <p className="text-xs text-muted">~{formatShortDate(charge.next_expected_date)}</p>
            </div>
            <p className="text-sm font-semibold">{formatMoney(charge.amount, charge.currency)}</p>
          </li>
        ))}
      </ul>
    </Link>
  );
}
