"use client";

import { useEffect, useState } from "react";
import useSWR from "swr";
import { AlertTriangle, Bell, BellOff, CheckCircle2, X } from "lucide-react";
import AuthGuard from "@/components/AuthGuard";
import { SkeletonList } from "@/components/Skeleton";
import { apiFetch, ApiError } from "@/lib/api";
import { disablePushNotifications, enablePushNotifications, getPushStatus, type PushStatus } from "@/lib/push";
import type { Alert } from "@/lib/types";

function PushToggle() {
  const [status, setStatus] = useState<PushStatus | "loading">("loading");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getPushStatus().then(setStatus);
  }, []);

  async function toggle() {
    setBusy(true);
    setError(null);
    try {
      if (status === "subscribed") {
        await disablePushNotifications();
      } else {
        await enablePushNotifications();
      }
      setStatus(await getPushStatus());
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo cambiar las notificaciones");
    } finally {
      setBusy(false);
    }
  }

  if (status === "loading" || status === "unsupported") return null;

  return (
    <div className="mb-4">
      <button
        onClick={toggle}
        disabled={busy || status === "denied"}
        className="flex w-full items-center gap-3 rounded-2xl border border-surface-border bg-surface px-4 py-3.5 text-left shadow-[var(--shadow-card)] transition disabled:opacity-50"
      >
        <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-brand-soft">
          {status === "subscribed" ? (
            <Bell className="h-4 w-4 text-brand" />
          ) : (
            <BellOff className="h-4 w-4 text-muted" />
          )}
        </span>
        <div className="flex-1">
          <p className="text-sm font-medium">
            {status === "denied"
              ? "Notificaciones bloqueadas"
              : status === "subscribed"
                ? "Notificaciones activadas"
                : "Activar notificaciones"}
          </p>
          <p className="text-xs text-muted">
            {status === "denied"
              ? "Actívalas desde los permisos del navegador"
              : status === "subscribed"
                ? "Toca para desactivarlas en este dispositivo"
                : "Recibe un aviso al instante cuando haya una alerta nueva"}
          </p>
        </div>
      </button>
      {error && <p className="mt-2 text-sm text-danger">{error}</p>}
    </div>
  );
}

function AlertasContent() {
  const { data: alerts, error: fetchError, mutate } = useSWR<Alert[]>("/api/alerts", apiFetch);
  const error = fetchError ? (fetchError instanceof ApiError ? fetchError.message : "No se pudieron cargar las alertas") : null;
  const [dismissing, setDismissing] = useState<string | null>(null);

  async function dismissAlert(alertId: string) {
    setDismissing(alertId);
    const previous = alerts;
    mutate(previous?.filter((a) => a.id !== alertId), { revalidate: false });
    try {
      await apiFetch(`/api/alerts/${encodeURIComponent(alertId)}`, { method: "DELETE" });
    } catch {
      mutate(previous, { revalidate: false });
    } finally {
      setDismissing(null);
    }
  }

  return (
    <main className="mx-auto max-w-lg px-4 pb-28 pt-6">
      <h1 className="mb-6 text-2xl font-semibold tracking-tight">Alertas</h1>

      <PushToggle />

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
            <div className="flex-1">
              <p className="text-sm font-medium">{alert.title}</p>
              <p className="text-xs text-muted">{alert.subtitle}</p>
            </div>
            <button
              onClick={() => dismissAlert(alert.id)}
              disabled={dismissing === alert.id}
              aria-label="Descartar alerta"
              className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-muted-soft transition hover:bg-surface-hover hover:text-muted disabled:opacity-50"
            >
              <X className="h-4 w-4" />
            </button>
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
