"use client";

import useSWR from "swr";
import { AlertTriangle, CheckCircle2 } from "lucide-react";
import AuthGuard from "@/components/AuthGuard";
import { SkeletonList } from "@/components/Skeleton";
import { apiFetch, ApiError } from "@/lib/api";
import type { Alert } from "@/lib/types";

function AlertasContent() {
  const { data: alerts, error: fetchError } = useSWR<Alert[]>("/api/alerts", apiFetch);
  const error = fetchError ? (fetchError instanceof ApiError ? fetchError.message : "No se pudieron cargar las alertas") : null;

  return (
    <main className="mx-auto max-w-lg px-4 pb-28 pt-6">
      <h1 className="mb-6 text-2xl font-semibold tracking-tight">Alertas</h1>

      {error && <p className="mb-4 text-sm text-danger">{error}</p>}
      {!alerts && <SkeletonList rows={3} />}
      {alerts?.length === 0 && (
        <div className="flex flex-col items-center rounded-2xl border border-dashed border-surface-border px-6 py-10 text-center">
          <span className="mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-success-soft">
            <CheckCircle2 className="h-6 w-6 text-success" />
          </span>
          <p className="text-sm text-muted">Todo en orden, sin alertas.</p>
        </div>
      )}

      <ul className="flex flex-col gap-2">
        {alerts?.map((alert) => (
          <li
            key={alert.id}
            className="flex items-start gap-3 rounded-2xl border border-surface-border bg-surface px-4 py-3.5 shadow-[var(--shadow-card)]"
          >
            <span className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-warning-soft">
              <AlertTriangle className="h-4 w-4 text-warning" />
            </span>
            <div>
              <p className="text-sm font-medium">{alert.title}</p>
              <p className="text-xs text-muted">{alert.subtitle}</p>
            </div>
          </li>
        ))}
      </ul>
    </main>
  );
}

export default function AlertasPage() {
  return (
    <AuthGuard>
      <AlertasContent />
    </AuthGuard>
  );
}
