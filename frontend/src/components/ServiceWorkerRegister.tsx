"use client";

import { useEffect } from "react";

export default function ServiceWorkerRegister() {
  useEffect(() => {
    if ("serviceWorker" in navigator) {
      navigator.serviceWorker.register("/sw.js").catch(() => {
        // instalar la PWA es un extra, no algo crítico para que la app funcione
      });
    }
  }, []);

  return null;
}
