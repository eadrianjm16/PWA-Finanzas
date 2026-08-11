"use client";

import { useState } from "react";
import { CategoryIcon, ICON_NAMES } from "@/lib/icons";
import type { Category } from "@/lib/types";

export default function CategoryEditor({
  category,
  onSave,
  onClose,
}: {
  category: Category | null;
  onSave: (name: string, iconName: string) => Promise<void>;
  onClose: () => void;
}) {
  const [name, setName] = useState(category?.name ?? "");
  const [iconName, setIconName] = useState(category?.system_icon_name ?? ICON_NAMES[0]);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  async function handleSave() {
    const trimmed = name.trim();
    if (!trimmed) {
      setError("Pon un nombre");
      return;
    }
    setSaving(true);
    setError(null);
    try {
      await onSave(trimmed, iconName);
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo guardar");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="fixed inset-0 z-30 flex flex-col bg-background">
      <div className="flex items-center justify-between border-b border-surface-border bg-surface px-4 py-3">
        <button onClick={onClose} className="text-sm font-medium text-muted">
          Cancelar
        </button>
        <h2 className="text-sm font-semibold">{category ? "Editar categoría" : "Nueva categoría"}</h2>
        <button onClick={handleSave} disabled={saving} className="text-sm font-semibold text-brand disabled:opacity-50">
          Guardar
        </button>
      </div>

      <div className="flex-1 overflow-y-auto px-4 py-5">
        <div className="mb-5 flex flex-col items-center">
          <span className="mb-3 flex h-16 w-16 items-center justify-center rounded-full bg-brand-soft">
            <CategoryIcon name={iconName} className="h-7 w-7 text-brand" />
          </span>
          <input
            autoFocus
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Nombre"
            className="w-full rounded-xl border border-surface-border bg-surface px-3 py-2.5 text-center text-sm font-medium outline-none focus:border-brand focus:ring-4 focus:ring-brand-soft"
          />
        </div>
        {error && <p className="mb-3 text-center text-sm text-danger">{error}</p>}

        <p className="mb-2 px-1 text-xs font-semibold text-muted">Icono</p>
        <div className="grid grid-cols-6 gap-2">
          {ICON_NAMES.map((icon) => (
            <button
              key={icon}
              onClick={() => setIconName(icon)}
              className={`flex aspect-square items-center justify-center rounded-xl border transition ${
                icon === iconName
                  ? "border-brand bg-brand text-brand-contrast"
                  : "border-surface-border bg-surface text-muted"
              }`}
              aria-label={icon}
            >
              <CategoryIcon name={icon} className="h-5 w-5" />
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
