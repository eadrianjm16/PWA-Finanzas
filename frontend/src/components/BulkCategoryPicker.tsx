"use client";

import { useEffect, useState } from "react";
import { X } from "lucide-react";
import { apiFetch, ApiError } from "@/lib/api";
import { CategoryIcon } from "@/lib/icons";
import type { Category } from "@/lib/types";

export default function BulkCategoryPicker({
  count,
  onPick,
  onClose,
}: {
  count: number;
  onPick: (categoryId: string) => Promise<void>;
  onClose: () => void;
}) {
  const [categories, setCategories] = useState<Category[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    apiFetch<Category[]>("/api/categories")
      .then(setCategories)
      .catch(() => setError("No se pudieron cargar las categorías"));
  }, []);

  async function pick(categoryId: string) {
    setSaving(true);
    setError(null);
    try {
      await onPick(categoryId);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo categorizar");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="fixed inset-0 z-30 flex flex-col bg-background">
      <div className="flex items-center justify-between border-b border-surface-border bg-surface px-4 py-3">
        <button
          onClick={onClose}
          className="flex h-9 w-9 items-center justify-center rounded-full text-muted transition hover:bg-surface-hover"
        >
          <X className="h-[18px] w-[18px]" />
        </button>
        <h2 className="text-sm font-semibold">
          Categorizar {count} movimiento{count === 1 ? "" : "s"}
        </h2>
        <div className="w-9" />
      </div>

      <div className="flex-1 overflow-y-auto px-4 py-5">
        <ul className="overflow-hidden rounded-2xl border border-surface-border bg-surface shadow-[var(--shadow-card)]">
          {categories?.map((category, index) => (
            <li key={category.id} className={index > 0 ? "border-t border-surface-border" : ""}>
              <button
                onClick={() => pick(category.id)}
                disabled={saving}
                className="flex w-full items-center gap-3 px-4 py-3 text-left text-sm transition hover:bg-surface-hover disabled:opacity-50"
              >
                <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-surface-hover">
                  <CategoryIcon name={category.system_icon_name} className="h-4 w-4 text-muted" />
                </span>
                <span className="flex-1 font-medium">{category.name}</span>
              </button>
            </li>
          ))}
        </ul>
        {error && <p className="mt-3 text-sm text-danger">{error}</p>}
      </div>
    </div>
  );
}
