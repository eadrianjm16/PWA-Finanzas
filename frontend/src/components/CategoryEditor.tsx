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
    <div className="fixed inset-0 z-30 flex flex-col bg-white dark:bg-neutral-950">
      <div className="flex items-center justify-between border-b border-neutral-200 px-4 py-3 dark:border-neutral-800">
        <button onClick={onClose} className="text-sm text-neutral-500">
          Cancelar
        </button>
        <h2 className="text-sm font-semibold">{category ? "Editar categoría" : "Nueva categoría"}</h2>
        <button onClick={handleSave} disabled={saving} className="text-sm font-semibold text-neutral-900 disabled:opacity-50 dark:text-white">
          Guardar
        </button>
      </div>

      <div className="flex-1 overflow-y-auto px-4 py-4">
        <input
          autoFocus
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Nombre"
          className="mb-4 w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm outline-none dark:border-neutral-700 dark:bg-neutral-900"
        />
        {error && <p className="mb-3 text-sm text-red-600">{error}</p>}

        <p className="mb-2 text-xs font-medium text-neutral-500">Icono</p>
        <div className="grid grid-cols-6 gap-2">
          {ICON_NAMES.map((icon) => (
            <button
              key={icon}
              onClick={() => setIconName(icon)}
              className={`flex aspect-square items-center justify-center rounded-lg border ${
                icon === iconName
                  ? "border-neutral-900 bg-neutral-900 text-white dark:border-white dark:bg-white dark:text-neutral-900"
                  : "border-neutral-200 text-neutral-600 dark:border-neutral-800 dark:text-neutral-300"
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
