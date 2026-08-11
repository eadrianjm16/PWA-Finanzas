"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { ChevronLeft, Mail } from "lucide-react";
import { apiFetch, ApiError } from "@/lib/api";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const result = await apiFetch<{ message: string }>("/api/auth/forgot-password", {
        method: "POST",
        body: JSON.stringify({ email }),
      });
      setMessage(result.message);
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
            <Mail className="h-7 w-7" strokeWidth={2} />
          </span>
          <h1 className="text-2xl font-semibold tracking-tight">Recuperar contraseña</h1>
          <p className="mt-1 text-sm text-muted">Te enviamos un enlace a tu email</p>
        </div>

        {message ? (
          <p className="rounded-2xl border border-surface-border bg-surface p-6 text-center text-sm shadow-[var(--shadow-card)]">
            {message}
          </p>
        ) : (
          <form
            onSubmit={handleSubmit}
            className="flex flex-col gap-4 rounded-2xl border border-surface-border bg-surface p-6 shadow-[var(--shadow-card)]"
          >
            <input
              type="email"
              autoFocus
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="Email"
              className="rounded-xl border border-surface-border bg-background px-4 py-3 text-base outline-none transition-colors focus:border-brand focus:ring-4 focus:ring-brand-soft"
            />
            {error && <p className="text-sm text-danger">{error}</p>}
            <button
              type="submit"
              disabled={loading}
              className="rounded-xl bg-brand px-4 py-3 font-medium text-brand-contrast shadow-[var(--shadow-card)] transition active:scale-[0.98] disabled:opacity-50"
            >
              {loading ? "Enviando…" : "Enviar enlace"}
            </button>
          </form>
        )}

        <Link href="/login" className="mt-4 flex items-center justify-center gap-1 text-sm font-medium text-muted">
          <ChevronLeft className="h-4 w-4" />
          Volver a entrar
        </Link>
      </div>
    </main>
  );
}
