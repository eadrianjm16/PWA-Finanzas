"use client";

import { useState } from "react";
import useSWR from "swr";
import AuthGuard from "@/components/AuthGuard";
import CategoryEditor from "@/components/CategoryEditor";
import { apiFetch, ApiError } from "@/lib/api";
import { CategoryIcon } from "@/lib/icons";
import type { Category } from "@/lib/types";

const OTROS_NAME = "Otros";

function CategoriasContent() {
  const { data: categories, mutate } = useSWR<Category[]>("/api/categories", apiFetch);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [editorTarget, setEditorTarget] = useState<Category | "new" | null>(null);
  const [recalculating, setRecalculating] = useState(false);

  async function saveCategory(name: string, systemIconName: string) {
    if (editorTarget === "new") {
      await apiFetch("/api/categories", {
        method: "POST",
        body: JSON.stringify({ name, system_icon_name: systemIconName }),
      });
    } else if (editorTarget) {
      await apiFetch(`/api/categories/${editorTarget.id}`, {
        method: "PATCH",
        body: JSON.stringify({ name, system_icon_name: systemIconName }),
      });
    }
    setEditorTarget(null);
    await mutate();
  }

  async function deleteCategory(category: Category) {
    if (!window.confirm(`¿Borrar "${category.name}"? Sus movimientos pasarán a "${OTROS_NAME}".`)) return;
    try {
      await apiFetch(`/api/categories/${category.id}`, { method: "DELETE" });
      await mutate();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo borrar la categoría");
    }
  }

  async function move(index: number, delta: number) {
    if (!categories) return;
    const target = index + delta;
    if (target < 0 || target >= categories.length) return;
    const reordered = [...categories];
    [reordered[index], reordered[target]] = [reordered[target], reordered[index]];
    await mutate(reordered, { revalidate: false });
    try {
      await apiFetch("/api/categories/reorder", {
        method: "PUT",
        body: JSON.stringify({ ordered_ids: reordered.map((c) => c.id) }),
      });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo reordenar");
      await mutate();
    }
  }

  async function recalculate() {
    setRecalculating(true);
    setNotice(null);
    setError(null);
    try {
      const result = await apiFetch<{ updated_count: number }>("/api/transactions/recategorize-uncategorized", {
        method: "POST",
      });
      setNotice(`Se actualizaron ${result.updated_count} movimiento(s).`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo recalcular");
    } finally {
      setRecalculating(false);
    }
  }

  return (
    <main className="mx-auto max-w-lg px-4 pb-24 pt-6">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-xl font-semibold">Categorías</h1>
        <button
          onClick={() => setEditorTarget("new")}
          className="rounded-full bg-neutral-900 px-4 py-2 text-sm font-medium text-white dark:bg-white dark:text-neutral-900"
        >
          + Nueva
        </button>
      </div>

      {notice && <p className="mb-4 rounded-lg bg-neutral-100 px-3 py-2 text-sm dark:bg-neutral-900">{notice}</p>}
      {error && <p className="mb-4 text-sm text-red-600">{error}</p>}
      {!categories && <p className="text-sm text-neutral-500">Cargando…</p>}

      <ul className="mb-6 divide-y divide-neutral-100 overflow-hidden rounded-xl border border-neutral-200 dark:divide-neutral-800 dark:border-neutral-800">
        {categories?.map((category, index) => (
          <li key={category.id} className="flex items-center gap-3 px-4 py-3">
            <button
              onClick={() => setEditorTarget(category)}
              className="flex flex-1 items-center gap-3 text-left"
            >
              <CategoryIcon name={category.system_icon_name} className="h-5 w-5 shrink-0 text-neutral-500" />
              <span className="text-sm font-medium">{category.name}</span>
            </button>
            <div className="flex items-center gap-1 text-neutral-400">
              <button onClick={() => move(index, -1)} disabled={index === 0} className="px-1 disabled:opacity-30" aria-label="Subir">
                ↑
              </button>
              <button
                onClick={() => move(index, 1)}
                disabled={index === (categories?.length ?? 0) - 1}
                className="px-1 disabled:opacity-30"
                aria-label="Bajar"
              >
                ↓
              </button>
              {category.name !== OTROS_NAME && (
                <button onClick={() => deleteCategory(category)} className="px-1 text-red-500" aria-label="Borrar">
                  ✕
                </button>
              )}
            </div>
          </li>
        ))}
      </ul>

      <button
        onClick={recalculate}
        disabled={recalculating}
        className="w-full rounded-xl border border-neutral-200 px-4 py-3 text-sm font-medium text-neutral-700 disabled:opacity-50 dark:border-neutral-800 dark:text-neutral-300"
      >
        {recalculating ? "Recalculando…" : "Recalcular categorías de movimientos existentes"}
      </button>
      <p className="mt-2 text-xs text-neutral-500">
        Vuelve a categorizar automáticamente los movimientos que no hayas categorizado a mano.
      </p>

      {editorTarget && (
        <CategoryEditor
          category={editorTarget === "new" ? null : editorTarget}
          onSave={saveCategory}
          onClose={() => setEditorTarget(null)}
        />
      )}
    </main>
  );
}

export default function CategoriasPage() {
  return (
    <AuthGuard>
      <CategoriasContent />
    </AuthGuard>
  );
}
