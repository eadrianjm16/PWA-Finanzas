"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, FormEvent, useState } from "react";
import { CheckCircle2, KeyRound } from "lucide-react";
import { apiFetch, ApiError } from "@/lib/api";

function ResetPasswordContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const token = searchParams.get("token") ?? "";

  const [newPassword, setNewPassword] = useState("");
  const [done, setDone] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    if (newPassword.length < 8) {
      setError("La contraseña debe tener al menos 8 caracteres");
      return;
    }
    setLoading(true);
    try {
      await apiFetch("/api/auth/reset-password", {
        method: "POST",
        body: JSON.stringify({ token, new_password: newPassword }),
      });
      setDone(true);
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
            {done ? <CheckCircle2 className="h-7 w-7" strokeWidth={2} /> : <KeyRound className="h-7 w-7" strokeWidth={2} />}
          </span>
          <h1 className="text-2xl font-semibold tracking-tight">Nueva contraseña</h1>
        </div>

        {done ? (
          <div className="flex flex-col gap-4 rounded-2xl border border-surface-border bg-surface p-6 text-center shadow-[var(--shadow-card)]">
            <p className="text-sm">Contraseña actualizada correctamente.</p>
            <button
              onClick={() => router.replace("/login")}
              className="rounded-xl bg-brand px-4 py-3 font-medium text-brand-contrast shadow-[var(--shadow-card)] transition active:scale-[0.98]"
            >
              Entrar
            </button>
          </div>
        ) : !token ? (
          <p className="rounded-2xl border border-surface-border bg-surface p-6 text-center text-sm text-danger shadow-[var(--shadow-card)]">
            Enlace inválido. Pide uno nuevo desde{" "}
            <Link href="/forgot-password" className="font-medium text-brand">
              recuperar contraseña
            </Link>
            .
          </p>
        ) : (
          <form
            onSubmit={handleSubmit}
            className="flex flex-col gap-4 rounded-2xl border border-surface-border bg-surface p-6 shadow-[var(--shadow-card)]"
          >
            <input
              type="password"
              autoFocus
              required
              minLength={8}
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              placeholder="Nueva contraseña (mínimo 8 caracteres)"
              className="rounded-xl border border-surface-border bg-background px-4 py-3 text-base outline-none transition-colors focus:border-brand focus:ring-4 focus:ring-brand-soft"
            />
            {error && <p className="text-sm text-danger">{error}</p>}
            <button
              type="submit"
              disabled={loading}
              className="rounded-xl bg-brand px-4 py-3 font-medium text-brand-contrast shadow-[var(--shadow-card)] transition active:scale-[0.98] disabled:opacity-50"
            >
              {loading ? "Guardando…" : "Guardar nueva contraseña"}
            </button>
          </form>
        )}
      </div>
    </main>
  );
}

export default function ResetPasswordPage() {
  return (
    <Suspense fallback={null}>
      <ResetPasswordContent />
    </Suspense>
  );
}
