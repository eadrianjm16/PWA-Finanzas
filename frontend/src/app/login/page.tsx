"use client";

import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";
import { Wallet } from "lucide-react";
import { ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";

export default function LoginPage() {
  const { login } = useAuth();
  const router = useRouter();
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await login(password);
      router.replace("/accounts");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo conectar con el servidor");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="flex min-h-screen flex-col items-center justify-center bg-background px-6">
      <div className="w-full max-w-sm">
        <div className="mb-8 flex flex-col items-center text-center">
          <span className="mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-brand text-brand-contrast shadow-[var(--shadow-pop)]">
            <Wallet className="h-7 w-7" strokeWidth={2} />
          </span>
          <h1 className="text-2xl font-semibold tracking-tight">Finanzas</h1>
          <p className="mt-1 text-sm text-muted">Accede con tu contraseña</p>
        </div>

        <form
          onSubmit={handleSubmit}
          className="flex flex-col gap-4 rounded-2xl border border-surface-border bg-surface p-6 shadow-[var(--shadow-card)]"
        >
          <input
            type="password"
            autoFocus
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Contraseña"
            className="rounded-xl border border-surface-border bg-background px-4 py-3 text-base outline-none transition-colors focus:border-brand focus:ring-4 focus:ring-brand-soft"
          />
          {error && <p className="text-sm text-danger">{error}</p>}
          <button
            type="submit"
            disabled={loading}
            className="rounded-xl bg-brand px-4 py-3 font-medium text-brand-contrast shadow-[var(--shadow-card)] transition active:scale-[0.98] disabled:opacity-50"
          >
            {loading ? "Entrando…" : "Entrar"}
          </button>
        </form>
      </div>
    </main>
  );
}
