"use client";

import { useEffect, useMemo, useState } from "react";
import { Landmark, Search, X } from "lucide-react";
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
    <div className="fixed inset-0 z-20 flex flex-col bg-background">
      <div className="flex items-center gap-2 border-b border-surface-border bg-surface px-4 py-3">
        <button
          onClick={onClose}
          className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full text-muted transition hover:bg-surface-hover"
          aria-label="Cerrar"
        >
          <X className="h-[18px] w-[18px]" />
        </button>
        <div className="relative flex-1">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-soft" />
          <input
            autoFocus
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Buscar banco…"
            className="w-full rounded-xl border border-surface-border bg-background py-2 pl-9 pr-3 text-sm outline-none focus:border-brand focus:ring-4 focus:ring-brand-soft"
          />
        </div>
      </div>

      {error && <p className="px-4 pt-3 text-sm text-danger">{error}</p>}

      <div className="flex-1 overflow-y-auto px-4 py-3">
        {loading ? (
          <p className="px-1 py-6 text-sm text-muted">Cargando bancos…</p>
        ) : (
          <ul className="overflow-hidden rounded-2xl border border-surface-border bg-surface shadow-[var(--shadow-card)]">
            {filtered.map((aspsp, index) => (
              <li key={`${aspsp.name}_${aspsp.country}`} className={index > 0 ? "border-t border-surface-border" : ""}>
                <button
                  onClick={() => connect(aspsp)}
                  disabled={connecting !== null}
                  className="flex w-full items-center gap-3 px-4 py-3.5 text-left text-sm transition hover:bg-surface-hover disabled:opacity-50"
                >
                  <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-surface-hover">
                    <Landmark className="h-4 w-4 text-muted" />
                  </span>
                  <span className="flex-1 font-medium">{aspsp.name}</span>
                  {connecting === aspsp.name && <span className="text-xs text-brand">Conectando…</span>}
                </button>
              </li>
            ))}
            {filtered.length === 0 && <li className="px-4 py-6 text-sm text-muted">Sin resultados</li>}
          </ul>
        )}
      </div>
    </div>
  );
}
