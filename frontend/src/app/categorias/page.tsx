"use client";

import { useState } from "react";
import useSWR from "swr";
import { ChevronDown, ChevronUp, Plus, RotateCw, Tag, X } from "lucide-react";
import AuthGuard from "@/components/AuthGuard";
import CategoryEditor from "@/components/CategoryEditor";
import { SkeletonList } from "@/components/Skeleton";
import { apiFetch, ApiError } from "@/lib/api";
import { CategoryIcon } from "@/lib/icons";
import type { Category, CategorizationRule } from "@/lib/types";

const OTROS_NAME = "Otros";

function CategorizationRulesSection({ categories }: { categories: Category[] | undefined }) {
  const { data: rules, mutate } = useSWR<CategorizationRule[]>("/api/categorization-rules", apiFetch);
  const [keyword, setKeyword] = useState("");
  const [categoryId, setCategoryId] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  async function addRule() {
    const trimmed = keyword.trim();
    if (!trimmed || !categoryId) return;
    setSaving(true);
    setError(null);
    setNotice(null);
    try {
      await apiFetch("/api/categorization-rules", {
        method: "POST",
        body: JSON.stringify({ keyword: trimmed, category_id: categoryId }),
      });
      setKeyword("");
      setCategoryId("");
      await mutate();
      // Sin esto, la regla nueva solo se notaría en sincronizaciones
      // futuras: se reaplica también sobre movimientos pasados que aún no
      // se hayan categorizado a mano, para que el análisis histórico use
      // la regla desde ya.
      const result = await apiFetch<{ updated_count: number }>("/api/transactions/recategorize-uncategorized", {
        method: "POST",
      });
      setNotice(
        result.updated_count > 0
          ? `Regla creada y aplicada a ${result.updated_count} movimiento(s) anteriores.`
          : "Regla creada."
      );
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo crear la regla");
    } finally {
      setSaving(false);
    }
  }

  async function deleteRule(id: string) {
    try {
      await apiFetch(`/api/categorization-rules/${id}`, { method: "DELETE" });
      await mutate();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo borrar la regla");
    }
  }

  return (
    <section className="mb-6">
      <h2 className="mb-2 px-1 text-sm font-semibold text-muted">Reglas de categorización</h2>
      <p className="mb-3 px-1 text-xs text-muted">
        Si el concepto de un movimiento contiene esta palabra, se categoriza así automáticamente — gana a la
        sugerencia por defecto. Al crear una regla también se aplica a tus movimientos pasados (los que no hayas
        categorizado a mano).
      </p>

      {rules && rules.length > 0 && (
        <ul className="mb-3 overflow-hidden rounded-2xl border border-surface-border bg-surface shadow-[var(--shadow-card)]">
          {rules.map((rule, index) => (
            <li
              key={rule.id}
              className={`flex items-center gap-3 px-4 py-3 ${index > 0 ? "border-t border-surface-border" : ""}`}
            >
              <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-surface-hover">
                <Tag className="h-3.5 w-3.5 text-muted" />
              </span>
              <p className="flex-1 text-sm">
                <span className="font-medium">&quot;{rule.keyword}&quot;</span>{" "}
                <span className="text-muted">→ {rule.category.name}</span>
              </p>
              <button
                onClick={() => deleteRule(rule.id)}
                aria-label="Borrar regla"
                className="flex h-7 w-7 items-center justify-center rounded-full text-danger transition hover:bg-danger-soft"
              >
                <X className="h-3.5 w-3.5" />
              </button>
            </li>
          ))}
        </ul>
      )}

      <div className="flex flex-col gap-2 rounded-2xl border border-surface-border bg-surface p-3 shadow-[var(--shadow-card)]">
        <div className="flex gap-2">
          <input
            value={keyword}
            onChange={(e) => setKeyword(e.target.value)}
            placeholder="Palabra clave (ej. UBER)"
            className="min-w-0 flex-1 rounded-xl border border-surface-border bg-background px-3 py-2 text-sm outline-none focus:border-brand focus:ring-4 focus:ring-brand-soft"
          />
          <select
            value={categoryId}
            onChange={(e) => setCategoryId(e.target.value)}
            className="rounded-xl border border-surface-border bg-background px-2 py-2 text-sm outline-none focus:border-brand focus:ring-4 focus:ring-brand-soft"
          >
            <option value="">Categoría…</option>
            {categories?.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </select>
        </div>
        {notice && <p className="text-sm text-brand">{notice}</p>}
        {error && <p className="text-sm text-danger">{error}</p>}
        <button
          onClick={addRule}
          disabled={saving || !keyword.trim() || !categoryId}
          className="rounded-xl bg-brand px-4 py-2 text-sm font-medium text-brand-contrast transition active:scale-[0.98] disabled:opacity-50"
        >
          {saving ? "Creando y aplicando…" : "Añadir regla"}
        </button>
      </div>
    </section>
  );
}

function CategoriasContent() {
  const { data: categories, mutate } = useSWR<Category[]>("/api/categories", apiFetch);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [editorTarget, setEditorTarget] = useState<Category | "new" | null>(null);
  const [recalculating, setRecalculating] = useState(false);
  const [applyingRules, setApplyingRules] = useState(false);

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

  async function applyRulesToAll() {
    if (
      !window.confirm(
        "Esto puede cambiar la categoría de movimientos que ya categorizaste a mano, si coinciden con alguna de tus reglas. ¿Continuar?"
      )
    ) {
      return;
    }
    setApplyingRules(true);
    setNotice(null);
    setError(null);
    try {
      const result = await apiFetch<{ updated_count: number }>("/api/transactions/apply-rules", {
        method: "POST",
      });
      setNotice(`Se actualizaron ${result.updated_count} movimiento(s) según tus reglas.`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudieron aplicar las reglas");
    } finally {
      setApplyingRules(false);
    }
  }

  return (
    <main className="mx-auto max-w-lg px-4 pb-28 pt-6">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-semibold tracking-tight">Categorías</h1>
        <button
          onClick={() => setEditorTarget("new")}
          className="flex items-center gap-1.5 rounded-full bg-brand px-4 py-2 text-sm font-medium text-brand-contrast shadow-[var(--shadow-card)] transition active:scale-95"
        >
          <Plus className="h-4 w-4" strokeWidth={2.5} />
          Nueva
        </button>
      </div>

      {notice && (
        <p className="mb-4 rounded-xl bg-brand-soft px-3.5 py-2.5 text-sm font-medium text-brand">{notice}</p>
      )}
      {error && <p className="mb-4 text-sm text-danger">{error}</p>}
      {!categories && <SkeletonList rows={6} />}

      <ul className="mb-6 overflow-hidden rounded-2xl border border-surface-border bg-surface shadow-[var(--shadow-card)]">
        {categories?.map((category, index) => (
          <li
            key={category.id}
            className={`flex items-center gap-2 px-4 py-3 ${index > 0 ? "border-t border-surface-border" : ""}`}
          >
            <button onClick={() => setEditorTarget(category)} className="flex flex-1 items-center gap-3 text-left">
              <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-surface-hover">
                <CategoryIcon name={category.system_icon_name} className="h-4 w-4 text-muted" />
              </span>
              <span className="text-sm font-medium">{category.name}</span>
            </button>
            <div className="flex items-center gap-0.5 text-muted-soft">
              <button
                onClick={() => move(index, -1)}
                disabled={index === 0}
                className="flex h-7 w-7 items-center justify-center rounded-full transition hover:bg-surface-hover disabled:opacity-30"
                aria-label="Subir"
              >
                <ChevronUp className="h-3.5 w-3.5" />
              </button>
              <button
                onClick={() => move(index, 1)}
                disabled={index === (categories?.length ?? 0) - 1}
                className="flex h-7 w-7 items-center justify-center rounded-full transition hover:bg-surface-hover disabled:opacity-30"
                aria-label="Bajar"
              >
                <ChevronDown className="h-3.5 w-3.5" />
              </button>
              {category.name !== OTROS_NAME && (
                <button
                  onClick={() => deleteCategory(category)}
                  className="flex h-7 w-7 items-center justify-center rounded-full text-danger transition hover:bg-danger-soft"
                  aria-label="Borrar"
                >
                  <X className="h-3.5 w-3.5" />
                </button>
              )}
            </div>
          </li>
        ))}
      </ul>

      <button
        onClick={recalculate}
        disabled={recalculating}
        className="mb-6 flex w-full items-center justify-center gap-2 rounded-2xl border border-surface-border bg-surface px-4 py-3.5 text-sm font-medium text-foreground shadow-[var(--shadow-card)] transition disabled:opacity-50"
      >
        <RotateCw className={`h-4 w-4 ${recalculating ? "animate-spin" : ""}`} />
        {recalculating ? "Recalculando…" : "Recalcular categorías de movimientos existentes"}
      </button>
      <p className="-mt-4 mb-4 px-1 text-xs text-muted">
        Vuelve a categorizar automáticamente los movimientos que no hayas categorizado a mano (aplica también tus
        reglas).
      </p>

      <button
        onClick={applyRulesToAll}
        disabled={applyingRules}
        className="mb-6 flex w-full items-center justify-center gap-2 rounded-2xl border border-surface-border bg-surface px-4 py-3.5 text-sm font-medium text-foreground shadow-[var(--shadow-card)] transition disabled:opacity-50"
      >
        <RotateCw className={`h-4 w-4 ${applyingRules ? "animate-spin" : ""}`} />
        {applyingRules ? "Aplicando…" : "Aplicar reglas a todo el histórico"}
      </button>
      <p className="-mt-4 mb-6 px-1 text-xs text-muted">
        A diferencia del botón de arriba, esta sí puede cambiar movimientos que categorizaste a mano si coinciden con
        una regla — úsalo cuando quieras que una regla mande sobre todo tu histórico, no solo lo nuevo.
      </p>

      <CategorizationRulesSection categories={categories} />

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
