"use client";

import { useCallback, useEffect, useState } from "react";
import AuthGuard from "@/components/AuthGuard";
import { apiFetch, ApiError } from "@/lib/api";
import type { Alert } from "@/lib/types";

function AlertasContent() {
  const [alerts, setAlerts] = useState<Alert[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const data = await apiFetch<Alert[]>("/api/alerts");
      setAlerts(data);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudieron cargar las alertas");
    }
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    load();
  }, [load]);

  return (
    <main className="mx-auto max-w-lg px-4 pb-24 pt-6">
      <h1 className="mb-6 text-xl font-semibold">Alertas</h1>

      {error && <p className="mb-4 text-sm text-red-600">{error}</p>}
      {alerts === null && <p className="text-sm text-neutral-500">Cargando…</p>}
      {alerts?.length === 0 && <p className="text-sm text-neutral-500">Todo en orden, sin alertas.</p>}

      <ul className="flex flex-col gap-2">
        {alerts?.map((alert) => (
          <li
            key={alert.id}
            className="flex items-start gap-3 rounded-xl border border-neutral-200 px-4 py-3 dark:border-neutral-800"
          >
            <span className="mt-1.5 h-2 w-2 shrink-0 rounded-full bg-amber-500" />
            <div>
              <p className="text-sm font-medium">{alert.title}</p>
              <p className="text-xs text-neutral-500">{alert.subtitle}</p>
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
