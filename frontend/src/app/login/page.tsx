"use client";

import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";
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
    <main className="flex min-h-screen flex-col items-center justify-center px-6">
      <div className="w-full max-w-sm">
        <h1 className="mb-1 text-2xl font-semibold">Finanzas</h1>
        <p className="mb-8 text-sm text-neutral-500">Accede con tu contraseña</p>

        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <input
            type="password"
            autoFocus
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Contraseña"
            className="rounded-xl border border-neutral-300 bg-white px-4 py-3 text-base outline-none focus:border-neutral-900 dark:border-neutral-700 dark:bg-neutral-900"
          />
          {error && <p className="text-sm text-red-600">{error}</p>}
          <button
            type="submit"
            disabled={loading}
            className="rounded-xl bg-neutral-900 px-4 py-3 font-medium text-white disabled:opacity-50 dark:bg-white dark:text-neutral-900"
          >
            {loading ? "Entrando…" : "Entrar"}
          </button>
        </form>
      </div>
    </main>
  );
}
