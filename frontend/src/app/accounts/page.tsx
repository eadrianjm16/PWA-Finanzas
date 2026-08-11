"use client";

import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import useSWR from "swr";
import { Eye, EyeOff, Landmark, MoreHorizontal, Plus, RefreshCw, Trash2, Wallet } from "lucide-react";
import AuthGuard from "@/components/AuthGuard";
import BankPicker from "@/components/BankPicker";
import { Skeleton, SkeletonList } from "@/components/Skeleton";
import { apiFetch, ApiError } from "@/lib/api";
import { formatMoney } from "@/lib/format";
import type { BankConnection } from "@/lib/types";

function AccountsContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { data: connections, mutate } = useSWR<BankConnection[]>("/api/banks/connections", apiFetch);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [pickerOpen, setPickerOpen] = useState(false);
  const [refreshing, setRefreshing] = useState<string | null>(null);
  const [expandedAccount, setExpandedAccount] = useState<string | null>(null);

  useEffect(() => {
    // Si venimos del redirect del banco, aviso + limpieza de la URL.
    /* eslint-disable react-hooks/set-state-in-effect */
    if (searchParams.get("connected")) {
      setNotice("Banco conectado correctamente.");
      router.replace("/accounts");
    } else if (searchParams.get("bank_error")) {
      setNotice(`No se pudo conectar el banco (${searchParams.get("bank_error")}).`);
      router.replace("/accounts");
    }
    /* eslint-enable react-hooks/set-state-in-effect */
  }, [searchParams, router]);

  async function refreshBalance(accountUid: string) {
    setRefreshing(accountUid);
    try {
      await apiFetch(`/api/accounts/${accountUid}/refresh-balance`, { method: "POST" });
      await mutate();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo actualizar el saldo");
    } finally {
      setRefreshing(null);
    }
  }

  async function toggleAccountFlag(accountUid: string, field: "is_visible" | "is_balance_visible", value: boolean) {
    try {
      await apiFetch(`/api/accounts/${accountUid}`, {
        method: "PATCH",
        body: JSON.stringify({ [field]: value }),
      });
      await mutate();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo actualizar la cuenta");
    }
  }

  async function deleteConnection(connection: BankConnection) {
    if (
      !window.confirm(
        `¿Eliminar ${connection.aspsp_name}? Se eliminará el historial de movimientos. Si lo vuelves a conectar, empezará de cero.`
      )
    )
      return;
    try {
      await apiFetch(`/api/banks/connections/${connection.id}`, { method: "DELETE" });
      await mutate();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo eliminar el banco");
    }
  }

  const total = (connections ?? [])
    .flatMap((c) => c.accounts)
    .filter((a) => a.is_visible && a.is_balance_visible && a.last_balance_amount)
    .reduce((sum, a) => sum + Number(a.last_balance_amount), 0);

  return (
    <main className="mx-auto max-w-lg px-4 pb-28 pt-6">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-semibold tracking-tight">Saldo</h1>
        <button
          onClick={() => setPickerOpen(true)}
          className="flex items-center gap-1.5 rounded-full bg-brand px-4 py-2 text-sm font-medium text-brand-contrast shadow-[var(--shadow-card)] transition active:scale-95"
        >
          <Plus className="h-4 w-4" strokeWidth={2.5} />
          Banco
        </button>
      </div>

      {notice && (
        <p className="mb-4 rounded-xl bg-brand-soft px-3.5 py-2.5 text-sm font-medium text-brand">{notice}</p>
      )}
      {error && <p className="mb-4 text-sm text-danger">{error}</p>}

      <div className="mb-8 overflow-hidden rounded-2xl bg-gradient-to-br from-brand to-brand-dark p-6 text-brand-contrast shadow-[var(--shadow-pop)]">
        <p className="mb-1 text-sm font-medium text-white/70">Saldo total</p>
        <p className="tabular-nums text-4xl font-semibold tracking-tight">{formatMoney(total, "EUR")}</p>
      </div>

      {!connections && <SkeletonList rows={3} />}

      {connections?.length === 0 && (
        <div className="flex flex-col items-center rounded-2xl border border-dashed border-surface-border px-6 py-10 text-center">
          <span className="mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-brand-soft">
            <Wallet className="h-6 w-6 text-brand" />
          </span>
          <p className="text-sm text-muted">Todavía no has conectado ningún banco.</p>
          <p className="text-sm text-muted">Toca &quot;Banco&quot; para empezar.</p>
        </div>
      )}

      <div className="flex flex-col gap-6">
        {connections?.map((connection) => (
          <section key={connection.id}>
            <div className="mb-2 flex items-center justify-between px-1">
              <h2 className="flex items-center gap-1.5 text-sm font-medium text-muted">
                <Landmark className="h-3.5 w-3.5" />
                {connection.aspsp_name}
              </h2>
              <button
                onClick={() => deleteConnection(connection)}
                className="flex items-center gap-1 text-xs font-medium text-danger"
              >
                <Trash2 className="h-3.5 w-3.5" />
                Eliminar
              </button>
            </div>
            <ul className="overflow-hidden rounded-2xl border border-surface-border bg-surface shadow-[var(--shadow-card)]">
              {connection.accounts.map((account, index) => (
                <li
                  key={account.account_uid}
                  className={`${index > 0 ? "border-t border-surface-border" : ""} ${account.is_visible ? "" : "opacity-40"}`}
                >
                  <div className="flex items-center justify-between px-4 py-3.5">
                    <div className="min-w-0">
                      <p className="truncate text-sm font-medium">{account.display_name}</p>
                      {account.iban && <p className="text-xs text-muted">····{account.iban.slice(-4)}</p>}
                      {account.last_sync_issue && <p className="text-xs text-danger">{account.last_sync_issue}</p>}
                    </div>
                    <div className="flex shrink-0 items-center gap-1.5">
                      <span className="tabular-nums text-sm font-semibold">
                        {account.is_visible && account.is_balance_visible && account.last_balance_amount
                          ? formatMoney(account.last_balance_amount, account.last_balance_currency ?? "EUR")
                          : "····"}
                      </span>
                      <button
                        onClick={() => refreshBalance(account.account_uid)}
                        disabled={refreshing === account.account_uid}
                        className="flex h-8 w-8 items-center justify-center rounded-full text-muted-soft transition hover:bg-surface-hover disabled:opacity-50"
                        aria-label="Actualizar saldo"
                      >
                        <RefreshCw className={`h-4 w-4 ${refreshing === account.account_uid ? "animate-spin" : ""}`} />
                      </button>
                      <button
                        onClick={() =>
                          setExpandedAccount(expandedAccount === account.account_uid ? null : account.account_uid)
                        }
                        className="flex h-8 w-8 items-center justify-center rounded-full text-muted-soft transition hover:bg-surface-hover"
                        aria-label="Más opciones"
                      >
                        <MoreHorizontal className="h-4 w-4" />
                      </button>
                    </div>
                  </div>

                  {expandedAccount === account.account_uid && (
                    <div className="flex flex-col gap-1 border-t border-surface-border px-4 py-3">
                      <button
                        onClick={() => toggleAccountFlag(account.account_uid, "is_visible", !account.is_visible)}
                        className="flex items-center justify-between py-1.5 text-sm"
                      >
                        <span>Ver esta cuenta</span>
                        {account.is_visible ? (
                          <Eye className="h-4 w-4 text-brand" />
                        ) : (
                          <EyeOff className="h-4 w-4 text-muted-soft" />
                        )}
                      </button>
                      {account.is_visible && (
                        <button
                          onClick={() =>
                            toggleAccountFlag(account.account_uid, "is_balance_visible", !account.is_balance_visible)
                          }
                          className="flex items-center justify-between py-1.5 text-sm"
                        >
                          <span>Ver saldo</span>
                          {account.is_balance_visible ? (
                            <Eye className="h-4 w-4 text-brand" />
                          ) : (
                            <EyeOff className="h-4 w-4 text-muted-soft" />
                          )}
                        </button>
                      )}
                    </div>
                  )}
                </li>
              ))}
            </ul>
          </section>
        ))}
      </div>

      {pickerOpen && <BankPicker onClose={() => setPickerOpen(false)} />}
    </main>
  );
}

export default function AccountsPage() {
  return (
    <AuthGuard>
      <Suspense fallback={<Skeleton className="mx-auto mt-6 h-40 w-full max-w-lg" />}>
        <AccountsContent />
      </Suspense>
    </AuthGuard>
  );
}
