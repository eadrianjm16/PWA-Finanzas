"""Detecta movimientos que probablemente sean traspasos entre las propias
cuentas del usuario (p. ej. Santander -> ING) - el "no computable" de
Fintonic. Puerto de InternalTransferDetector.swift.

Enable Banking no marca esto explicitamente: se infiere emparejando un
cargo en una cuenta con un abono en OTRA cuenta propia, mismo importe y
moneda, fecha cercana (misma ventana de 3 dias que AlertsEngine usa para
duplicados). No es infalible, pero es una señal razonable para uso
personal con pocas cuentas.
"""

from datetime import timedelta

from . import models

WINDOW = timedelta(days=3)


def detect(transactions: list[models.Transaction]) -> set[str]:
    flagged: set[str] = set()
    grouped: dict[str, list[models.Transaction]] = {}
    for tx in transactions:
        grouped.setdefault(f"{tx.amount}|{tx.currency}", []).append(tx)

    for group in grouped.values():
        if len(group) < 2:
            continue
        for a in group:
            if a.entry_reference in flagged:
                continue
            for b in group:
                if (
                    b.entry_reference != a.entry_reference
                    and a.account_uid != b.account_uid
                    and a.credit_debit_indicator != b.credit_debit_indicator
                    and abs(a.booking_date - b.booking_date) <= WINDOW
                ):
                    flagged.add(a.entry_reference)
                    flagged.add(b.entry_reference)
                    break
    return flagged
