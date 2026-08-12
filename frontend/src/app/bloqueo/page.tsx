"use client";

import { useEffect, useState } from "react";
import { Lock, ShieldCheck } from "lucide-react";
import AuthGuard from "@/components/AuthGuard";
import { clearPin, hasPinSet, setPin, verifyPin } from "@/lib/pinLock";

function BloqueoContent() {
  const [active, setActive] = useState(false);
  const [mode, setMode] = useState<"idle" | "create" | "confirm" | "remove">("idle");
  const [firstPin, setFirstPin] = useState("");
  const [input, setInput] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- localStorage solo existe en cliente
    setActive(hasPinSet());
  }, []);

  function startCreate() {
    setMode("create");
    setInput("");
    setError(null);
  }

  function handleCreateStep(event: React.FormEvent) {
    event.preventDefault();
    if (input.length < 4) return;
    setFirstPin(input);
    setInput("");
    setMode("confirm");
  }

  async function handleConfirmStep(event: React.FormEvent) {
    event.preventDefault();
    if (input !== firstPin) {
      setError("No coincide con el PIN anterior");
      setInput("");
      setMode("create");
      setFirstPin("");
      return;
    }
    await setPin(input);
    setActive(true);
    setMode("idle");
    setInput("");
    setFirstPin("");
    setError(null);
  }

  function startRemove() {
    setMode("remove");
    setInput("");
    setError(null);
  }

  async function handleRemoveStep(event: React.FormEvent) {
    event.preventDefault();
    if (await verifyPin(input)) {
      clearPin();
      setActive(false);
      setMode("idle");
      setInput("");
      setError(null);
    } else {
      setError("PIN incorrecto");
      setInput("");
    }
  }

  return (
    <main className="mx-auto max-w-lg px-4 pb-28 pt-6">
      <h1 className="mb-1 text-2xl font-semibold tracking-tight">Bloqueo con PIN</h1>
      <p className="mb-6 text-sm text-muted">
        Pide un PIN al abrir la app tras un rato en segundo plano. No sustituye tu contraseña — es solo para que
        nadie vea tus datos si te dejas el móvil desbloqueado.
      </p>

      <div className="mb-6 flex items-center gap-3 rounded-2xl border border-surface-border bg-surface px-4 py-3.5 shadow-[var(--shadow-card)]">
        <span className="flex h-9 w-9 items-center justify-center rounded-full bg-brand-soft">
          {active ? <ShieldCheck className="h-4 w-4 text-brand" /> : <Lock className="h-4 w-4 text-muted" />}
        </span>
        <p className="text-sm font-medium">{active ? "Bloqueo activado" : "Bloqueo desactivado"}</p>
      </div>

      {mode === "idle" && (
        <button
          onClick={active ? startRemove : startCreate}
          className="w-full rounded-xl bg-brand px-4 py-3 text-sm font-medium text-brand-contrast shadow-[var(--shadow-card)] transition active:scale-[0.98]"
        >
          {active ? "Quitar PIN" : "Crear PIN"}
        </button>
      )}

      {(mode === "create" || mode === "confirm") && (
        <form onSubmit={mode === "create" ? handleCreateStep : handleConfirmStep} className="flex flex-col gap-3">
          <p className="text-sm text-muted">{mode === "create" ? "Elige un PIN de 4 a 6 dígitos" : "Repítelo para confirmar"}</p>
          <input
            type="password"
            inputMode="numeric"
            autoFocus
            maxLength={6}
            value={input}
            onChange={(e) => setInput(e.target.value.replace(/\D/g, ""))}
            placeholder="••••"
            className="w-full rounded-xl border border-surface-border bg-surface px-4 py-3 text-center text-2xl tracking-[0.5em] outline-none transition-colors focus:border-brand focus:ring-4 focus:ring-brand-soft"
          />
          {error && <p className="text-sm text-danger">{error}</p>}
          <button
            type="submit"
            disabled={input.length < 4}
            className="rounded-xl bg-brand px-4 py-3 text-sm font-medium text-brand-contrast shadow-[var(--shadow-card)] transition active:scale-[0.98] disabled:opacity-50"
          >
            Continuar
          </button>
        </form>
      )}

      {mode === "remove" && (
        <form onSubmit={handleRemoveStep} className="flex flex-col gap-3">
          <p className="text-sm text-muted">Introduce tu PIN actual para quitarlo</p>
          <input
            type="password"
            inputMode="numeric"
            autoFocus
            maxLength={6}
            value={input}
            onChange={(e) => setInput(e.target.value.replace(/\D/g, ""))}
            placeholder="••••"
            className="w-full rounded-xl border border-surface-border bg-surface px-4 py-3 text-center text-2xl tracking-[0.5em] outline-none transition-colors focus:border-brand focus:ring-4 focus:ring-brand-soft"
          />
          {error && <p className="text-sm text-danger">{error}</p>}
          <button
            type="submit"
            disabled={input.length < 4}
            className="rounded-xl bg-danger px-4 py-3 text-sm font-medium text-white shadow-[var(--shadow-card)] transition active:scale-[0.98] disabled:opacity-50"
          >
            Quitar PIN
          </button>
        </form>
      )}
    </main>
  );
}

export default function BloqueoPage() {
  return (
    <AuthGuard>
      <BloqueoContent />
    </AuthGuard>
  );
}
