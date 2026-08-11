"use client";

import { SWRConfig } from "swr";
import type { Cache, State } from "swr";
import type { ReactNode } from "react";

const CACHE_KEY = "finanzas-swr-cache";

export function clearPersistedSWRCache(): void {
  if (typeof window !== "undefined") localStorage.removeItem(CACHE_KEY);
}

function localStorageProvider(): Cache {
  const map = new Map<string, State>(
    typeof window !== "undefined" ? JSON.parse(localStorage.getItem(CACHE_KEY) || "[]") : []
  );

  if (typeof window !== "undefined") {
    // pagehide + visibilitychange en vez de beforeunload: en Safari/Chrome
    // moviles, una pestaña en segundo plano se puede descargar de memoria
    // sin disparar beforeunload, pero estos dos eventos si son fiables ahi.
    const persist = () => {
      try {
        localStorage.setItem(CACHE_KEY, JSON.stringify(Array.from(map.entries())));
      } catch {
        // localStorage lleno o no disponible: se pierde la cache, no es critico.
      }
    };
    window.addEventListener("pagehide", persist);
    document.addEventListener("visibilitychange", () => {
      if (document.visibilityState === "hidden") persist();
    });
  }

  return map;
}

export default function SWRProvider({ children }: { children: ReactNode }) {
  return <SWRConfig value={{ provider: localStorageProvider }}>{children}</SWRConfig>;
}
