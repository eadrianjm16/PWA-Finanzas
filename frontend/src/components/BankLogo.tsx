"use client";

import { useState } from "react";
import { Landmark } from "lucide-react";

export default function BankLogo({ src, alt, className }: { src: string | null | undefined; alt: string; className?: string }) {
  const [failedSrc, setFailedSrc] = useState<string | null>(null);
  const [trackedSrc, setTrackedSrc] = useState(src);

  // Ajuste de estado durante el render (no en un efecto): si `src` cambia,
  // se olvida el fallo anterior en el mismo render, sin el flicker de un
  // efecto aparte. Sin esto, un fallo puntual de carga (p. ej. red
  // inestable la primera vez) dejaba el icono generico fijo para siempre en
  // esa sesion, aunque `src` cambiase despues a una URL que sí carga.
  if (src !== trackedSrc) {
    setTrackedSrc(src);
    setFailedSrc(null);
  }

  if (!src || failedSrc === src) {
    return <Landmark className={className ?? "h-4 w-4 text-muted"} />;
  }

  // eslint-disable-next-line @next/next/no-img-element -- logo viene de un dominio externo (Enable Banking), no del propio sitio
  return <img src={src} alt={alt} onError={() => setFailedSrc(src)} className={`object-contain ${className ?? "h-4 w-4"}`} />;
}
