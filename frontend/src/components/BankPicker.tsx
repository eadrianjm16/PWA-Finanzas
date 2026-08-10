"use client";

import { useEffect, useMemo, useState } from "react";
import { apiFetch, ApiError } from "@/lib/api";
import type { ASPSP } from "@/lib/types";

export default function BankPicker({ onClose }: { onClose: () => void }) {
  const [aspsps, setAspsps] = useState<ASPSP[]>([]);
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const [connecting, setConnecting] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiFetch<ASPSP[]>("/api/banks/aspsps?country=ES")
      .then(setAspsps)
      .catch((err) => setError(err instanceof ApiError ? err.message : "No se pudo cargar la lista de bancos"))
      .finally(() => setLoading(false));
  }, []);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return aspsps;
    return aspsps.filter((a) => a.name.toLowerCase().includes(q));
  }, [aspsps, query]);

  async function connect(aspsp: ASPSP) {
    setConnecting(aspsp.name);
    setError(null);
    try {
      const result = await apiFetch<{ url: string }>("/api/banks/authorize", {
        method: "POST",
        body: JSON.stringify({ aspsp: { name: aspsp.name, country: aspsp.country, logo: aspsp.logo, bic: aspsp.bic } }),
      });
      // Navegación real a la pantalla de consentimiento del banco, fuera de React.
      // eslint-disable-next-line react-hooks/immutability
      window.location.href = result.url;
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo iniciar la conexión con el banco");
      setConnecting(null);
    }
  }

  return (
    <div className="fixed inset-0 z-20 flex flex-col bg-white dark:bg-neutral-950">
      <div className="flex items-center gap-3 border-b border-neutral-200 px-4 py-3 dark:border-neutral-800">
        <button onClick={onClose} className="text-sm text-neutral-500" aria-label="Cerrar">
          Cerrar
        </button>
        <input
          autoFocus
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Buscar banco…"
          className="flex-1 rounded-lg border border-neutral-300 px-3 py-2 text-sm outline-none dark:border-neutral-700 dark:bg-neutral-900"
        />
      </div>

      {error && <p className="px-4 pt-3 text-sm text-red-600">{error}</p>}

      <div className="flex-1 overflow-y-auto">
        {loading ? (
          <p className="px-4 py-6 text-sm text-neutral-500">Cargando bancos…</p>
        ) : (
          <ul className="divide-y divide-neutral-100 dark:divide-neutral-900">
            {filtered.map((aspsp) => (
              <li key={`${aspsp.name}_${aspsp.country}`}>
                <button
                  onClick={() => connect(aspsp)}
                  disabled={connecting !== null}
                  className="flex w-full items-center justify-between px-4 py-3 text-left text-sm disabled:opacity-50"
                >
                  <span>{aspsp.name}</span>
                  {connecting === aspsp.name && <span className="text-neutral-400">Conectando…</span>}
                </button>
              </li>
            ))}
            {filtered.length === 0 && (
              <li className="px-4 py-6 text-sm text-neutral-500">Sin resultados</li>
            )}
          </ul>
        )}
      </div>
    </div>
  );
}
