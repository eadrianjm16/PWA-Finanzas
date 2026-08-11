"use client";

import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import useSWR from "swr";
import AuthGuard from "@/components/AuthGuard";
import BankPicker from "@/components/BankPicker";
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
    <main className="mx-auto max-w-lg px-4 pb-24 pt-6">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-xl font-semibold">Saldo</h1>
        <button
          onClick={() => setPickerOpen(true)}
          className="rounded-full bg-neutral-900 px-4 py-2 text-sm font-medium text-white dark:bg-white dark:text-neutral-900"
        >
          + Banco
        </button>
      </div>

      {notice && <p className="mb-4 rounded-lg bg-neutral-100 px-3 py-2 text-sm dark:bg-neutral-900">{notice}</p>}
      {error && <p className="mb-4 text-sm text-red-600">{error}</p>}

      <p className="mb-8 text-3xl font-semibold">{formatMoney(total, "EUR")}</p>

      {!connections && <p className="text-sm text-neutral-500">Cargando…</p>}
      {connections?.length === 0 && (
        <p className="text-sm text-neutral-500">
          Todavía no has conectado ningún banco. Toca &quot;+ Banco&quot; para empezar.
        </p>
      )}

      <div className="flex flex-col gap-6">
        {connections?.map((connection) => (
          <section key={connection.id}>
            <div className="mb-2 flex items-center justify-between">
              <h2 className="text-sm font-medium text-neutral-500">{connection.aspsp_name}</h2>
              <button onClick={() => deleteConnection(connection)} className="text-xs text-red-600">
                Eliminar
              </button>
            </div>
            <ul className="divide-y divide-neutral-100 overflow-hidden rounded-xl border border-neutral-200 dark:divide-neutral-800 dark:border-neutral-800">
              {connection.accounts.map((account) => (
                <li key={account.account_uid} className={account.is_visible ? "" : "opacity-50"}>
                  <div className="flex items-center justify-between px-4 py-3">
                    <div>
                      <p className="text-sm font-medium">{account.display_name}</p>
                      {account.iban && <p className="text-xs text-neutral-500">····{account.iban.slice(-4)}</p>}
                      {account.last_sync_issue && <p className="text-xs text-red-600">{account.last_sync_issue}</p>}
                    </div>
                    <div className="flex items-center gap-3">
                      <span className="text-sm font-medium">
                        {account.is_visible && account.is_balance_visible && account.last_balance_amount
                          ? formatMoney(account.last_balance_amount, account.last_balance_currency ?? "EUR")
                          : "····"}
                      </span>
                      <button
                        onClick={() => refreshBalance(account.account_uid)}
                        disabled={refreshing === account.account_uid}
                        className="text-xs text-neutral-400 disabled:opacity-50"
                        aria-label="Actualizar saldo"
                      >
                        {refreshing === account.account_uid ? "…" : "↻"}
                      </button>
                      <button
                        onClick={() =>
                          setExpandedAccount(expandedAccount === account.account_uid ? null : account.account_uid)
                        }
                        className="text-xs text-neutral-400"
                        aria-label="Más opciones"
                      >
                        ⋯
                      </button>
                    </div>
                  </div>

                  {expandedAccount === account.account_uid && (
                    <div className="flex flex-col gap-2 border-t border-neutral-100 px-4 py-3 dark:border-neutral-900">
                      <label className="flex items-center justify-between text-sm">
                        Ver mi cuenta
                        <input
                          type="checkbox"
                          checked={account.is_visible}
                          onChange={(e) => toggleAccountFlag(account.account_uid, "is_visible", e.target.checked)}
                        />
                      </label>
                      {account.is_visible && (
                        <label className="flex items-center justify-between text-sm">
                          Ver saldo
                          <input
                            type="checkbox"
                            checked={account.is_balance_visible}
                            onChange={(e) =>
                              toggleAccountFlag(account.account_uid, "is_balance_visible", e.target.checked)
                            }
                          />
                        </label>
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
      <Suspense fallback={null}>
        <AccountsContent />
      </Suspense>
    </AuthGuard>
  );
}
