"""Resumen mensual de ingresos/gastos para la pantalla de Análisis: totales,
últimos 6 meses y desglose por categoría. Excluye cuentas ocultas
(is_visible) y traspasos entre cuentas propias ("no computable"), igual
que el resto de la app."""

from calendar import monthrange
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from . import models
from .internal_transfers import detect as detect_internal_transfers


def _month_bounds(year: int, month: int) -> tuple[datetime, datetime]:
    start = datetime(year, month, 1, tzinfo=timezone.utc)
    last_day = monthrange(year, month)[1]
    end = datetime(year, month, last_day, 23, 59, 59, tzinfo=timezone.utc)
    return start, end


def _visible_transactions(db: Session, start: datetime, end: datetime) -> list[models.Transaction]:
    return (
        db.query(models.Transaction)
        .join(models.LinkedAccount)
        .filter(models.LinkedAccount.is_visible.is_(True))
        .filter(models.Transaction.booking_date >= start)
        .filter(models.Transaction.booking_date <= end)
        .all()
    )


def _month_totals(db: Session, year: int, month: int) -> tuple[float, float]:
    """Solo income/expense (usado en la serie de 6 meses, sin desglosar no_computable)."""
    start, end = _month_bounds(year, month)
    income = 0.0
    expense = 0.0
    for tx in _visible_transactions(db, start, end):
        amount = abs(float(tx.amount))
        if tx.credit_debit_indicator == "CRDT":
            income += amount
        else:
            expense += amount
    return income, expense


def _previous_months(year: int, month: int, count: int) -> list[tuple[int, int]]:
    months = []
    y, m = year, month
    for _ in range(count):
        months.append((y, m))
        m -= 1
        if m == 0:
            m = 12
            y -= 1
    return list(reversed(months))


def build_summary(db: Session, year: int, month: int) -> dict:
    start, end = _month_bounds(year, month)
    transactions = _visible_transactions(db, start, end)
    internal_transfer_refs = detect_internal_transfers(transactions)

    income = expense = no_computable = 0.0
    spend_by_category: dict[str, float] = {}
    for tx in transactions:
        amount = abs(float(tx.amount))
        if tx.entry_reference in internal_transfer_refs:
            no_computable += amount
            continue
        if tx.credit_debit_indicator == "CRDT":
            income += amount
        else:
            expense += amount
            if tx.category_id is not None:
                spend_by_category[tx.category_id] = spend_by_category.get(tx.category_id, 0) + amount

    budgets = db.query(models.Budget).all()
    budgeted_total = sum(float(b.monthly_limit) for b in budgets)
    budget_used_ratio = (expense / budgeted_total) if budgeted_total > 0 else None

    last_six_months = []
    for y, m in _previous_months(year, month, 6):
        month_income, month_expense = _month_totals(db, y, m)
        last_six_months.append(
            {
                "month": f"{y:04d}-{m:02d}",
                "income": month_income,
                "expense": month_expense,
                "net": month_income - month_expense,
            }
        )

    categories = {c.id: c for c in db.query(models.Category).all()}
    breakdown = [
        {"category": categories[category_id], "spent": spent}
        for category_id, spent in sorted(spend_by_category.items(), key=lambda kv: -kv[1])
        if category_id in categories
    ]

    return {
        "month": f"{year:04d}-{month:02d}",
        "income": income,
        "expense": expense,
        "net": income - expense,
        "no_computable": no_computable,
        "budgeted_total": budgeted_total,
        "budget_used_ratio": budget_used_ratio,
        "last_six_months": last_six_months,
        "category_breakdown": breakdown,
    }
