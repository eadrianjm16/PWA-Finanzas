"use client";

import { useEffect, useState } from "react";
import { Lock } from "lucide-react";
import { useAuth } from "@/lib/auth";
import { hasPinSet, markHiddenNow, shouldRelockAfterHidden, UNLOCK_KEY, verifyPin } from "@/lib/pinLock";

export default function AppLock({ children }: { children: React.ReactNode }) {
  const { isAuthenticated } = useAuth();
  const [ready, setReady] = useState(false);
  const [locked, setLocked] = useState(false);
  const [pin, setPinInput] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // El hash del PIN vive en localStorage (solo cliente): hay que leerlo
    // tras montar para no desincronizar el render SSR.
    /* eslint-disable react-hooks/set-state-in-effect */
    if (!isAuthenticated || !hasPinSet()) {
      setLocked(false);
      setReady(true);
      return;
    }
    const alreadyUnlocked = sessionStorage.getItem(UNLOCK_KEY) === "1";
    setLocked(!alreadyUnlocked);
    setReady(true);
    /* eslint-enable react-hooks/set-state-in-effect */
  }, [isAuthenticated]);

  useEffect(() => {
    function onVisibilityChange() {
      if (document.hidden) {
        markHiddenNow();
        return;
      }
      if (hasPinSet() && shouldRelockAfterHidden()) {
        sessionStorage.removeItem(UNLOCK_KEY);
        setLocked(true);
      }
    }
    document.addEventListener("visibilitychange", onVisibilityChange);
    return () => document.removeEventListener("visibilitychange", onVisibilityChange);
  }, []);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    if (await verifyPin(pin)) {
      sessionStorage.setItem(UNLOCK_KEY, "1");
      setLocked(false);
      setPinInput("");
      setError(null);
    } else {
      setError("PIN incorrecto");
      setPinInput("");
    }
  }

  if (!ready || !locked) return <>{children}</>;

  return (
    <main className="flex min-h-screen flex-col items-center justify-center bg-background px-6">
      {/* eslint-disable-next-line @next/next/no-img-element -- icono estatico servido tal cual, no necesita optimizacion de next/image */}
      <img src="/icons/icon.svg" alt="App Bank" className="mb-5 h-14 w-14 rounded-2xl shadow-[var(--shadow-pop)]" />
      <span className="mb-3 flex h-9 w-9 items-center justify-center rounded-full bg-surface-hover">
        <Lock className="h-4 w-4 text-muted" />
      </span>
      <h1 className="mb-6 text-lg font-semibold tracking-tight">Introduce tu PIN</h1>
      <form onSubmit={handleSubmit} className="w-full max-w-xs">
        <input
          type="password"
          inputMode="numeric"
          autoFocus
          maxLength={6}
          value={pin}
          onChange={(e) => setPinInput(e.target.value.replace(/\D/g, ""))}
          placeholder="••••"
          className="w-full rounded-xl border border-surface-border bg-surface px-4 py-3 text-center text-2xl tracking-[0.5em] outline-none transition-colors focus:border-brand focus:ring-4 focus:ring-brand-soft"
        />
        {error && <p className="mt-3 text-center text-sm text-danger">{error}</p>}
        <button
          type="submit"
          disabled={pin.length < 4}
          className="mt-4 w-full rounded-xl bg-brand px-4 py-3 font-medium text-brand-contrast shadow-[var(--shadow-card)] transition active:scale-[0.98] disabled:opacity-50"
        >
          Desbloquear
        </button>
      </form>
    </main>
  );
}
