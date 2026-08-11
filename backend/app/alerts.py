"""Alertas calculadas al vuelo a partir de movimientos y presupuestos, sin
persistencia ni push real. Puerto de AlertsEngine.swift."""

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from . import models

DUPLICATE_WINDOW = timedelta(days=3)
BUDGET_ALERT_THRESHOLD = 0.8


def _normalized_text(text: str) -> str:
    upper = text.upper()
    return "".join(ch for ch in upper if ch.isalpha() or ch == " ")[:20]


def _visible_transactions_this_month(db: Session, user_id: str) -> list[models.Transaction]:
    now = datetime.now(timezone.utc)
    start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return (
        db.query(models.Transaction)
        .join(models.LinkedAccount)
        .filter(models.LinkedAccount.user_id == user_id)
        .filter(models.LinkedAccount.is_visible.is_(True))
        .filter(models.Transaction.booking_date >= start)
        .all()
    )


def budget_threshold_alerts(db: Session, user_id: str) -> list[dict]:
    budgets = db.query(models.Budget).join(models.Category).filter(models.Category.user_id == user_id).all()
    if not budgets:
        return []

    spend_by_category: dict[str, float] = {}
    for tx in _visible_transactions_this_month(db, user_id):
        if tx.credit_debit_indicator != "DBIT" or tx.category_id is None:
            continue
        spend_by_category[tx.category_id] = spend_by_category.get(tx.category_id, 0) + abs(float(tx.amount))

    month_key = datetime.now(timezone.utc).strftime("%Y-%m")
    alerts = []
    for budget in budgets:
        spent = spend_by_category.get(budget.category_id)
        limit = float(budget.monthly_limit)
        if not spent or limit <= 0:
            continue
        ratio = spent / limit
        if ratio < BUDGET_ALERT_THRESHOLD:
            continue
        percent = round(ratio * 100)
        title = (
            f"Presupuesto de {budget.category.name} superado"
            if ratio >= 1
            else f"Vas al {percent}% de tu presupuesto en {budget.category.name}"
        )
        alerts.append(
            {
                "id": f"budget-{budget.category_id}-{month_key}",
                "icon": "budget-over" if ratio >= 1 else "budget-warning",
                "title": title,
                "subtitle": f"{spent:.2f} de {limit:.2f} EUR este mes",
            }
        )
    return alerts


def duplicate_charge_alerts(db: Session, user_id: str) -> list[dict]:
    candidates = [
        tx
        for tx in _visible_transactions_this_month(db, user_id)
        if tx.credit_debit_indicator == "DBIT" and (tx.category is None or tx.category.name != "Suscripciones")
    ]

    grouped: dict[str, list[models.Transaction]] = {}
    for tx in candidates:
        key = f"{tx.amount}|{tx.currency}|{_normalized_text(tx.counterparty_name or tx.remittance_information)}"
        grouped.setdefault(key, []).append(tx)

    alerts = []
    for key, group in grouped.items():
        if len(group) < 2:
            continue
        group.sort(key=lambda t: t.booking_date)
        for i in range(1, len(group)):
            gap = group[i].booking_date - group[i - 1].booking_date
            if gap > DUPLICATE_WINDOW:
                continue
            name = (group[i].counterparty_name or group[i].remittance_information).strip()
            days = max(1, -(-gap.total_seconds() // 86400))  # ceil en días
            alerts.append(
                {
                    "id": f"dup-{key}-{i}",
                    "icon": "duplicate",
                    "title": "Posible cargo duplicado",
                    "subtitle": f"{name}: {group[i].amount} {group[i].currency} dos veces en {int(days)} día(s)",
                }
            )
            break  # una alerta por grupo basta
    return alerts


def bank_fee_alerts(db: Session, user_id: str) -> list[dict]:
    one_month_ago = datetime.now(timezone.utc) - timedelta(days=30)
    fees = (
        db.query(models.Transaction)
        .join(models.LinkedAccount)
        .join(models.Category)
        .filter(models.LinkedAccount.user_id == user_id)
        .filter(models.LinkedAccount.is_visible.is_(True))
        .filter(models.Category.name == "Comisiones bancarias")
        .filter(models.Transaction.booking_date >= one_month_ago)
        .all()
    )
    return [
        {
            "id": f"fee-{tx.entry_reference}",
            "icon": "bank-fee",
            "title": "Comisión bancaria detectada",
            "subtitle": f"{tx.amount} {tx.currency} el {tx.booking_date.strftime('%d/%m/%Y')}",
        }
        for tx in fees
    ]


def evaluate_alerts(db: Session, user_id: str) -> list[dict]:
    return budget_threshold_alerts(db, user_id) + duplicate_charge_alerts(db, user_id) + bank_fee_alerts(db, user_id)
