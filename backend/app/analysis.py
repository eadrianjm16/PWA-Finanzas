"""Resumen mensual de ingresos/gastos para la pantalla de Análisis: totales,
últimos 6 meses y desglose por categoría. Excluye cuentas ocultas
(is_visible) y traspasos entre cuentas propias ("no computable"), igual
que el resto de la app."""

from calendar import monthrange
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from . import models
from .budget_calc import effective_limit, spent_by_category_previous_month
from .internal_transfers import detect as detect_internal_transfers


def _month_bounds(year: int, month: int) -> tuple[datetime, datetime]:
    start = datetime(year, month, 1, tzinfo=timezone.utc)
    last_day = monthrange(year, month)[1]
    end = datetime(year, month, last_day, 23, 59, 59, tzinfo=timezone.utc)
    return start, end


def _visible_transactions(db: Session, user_id: str, start: datetime, end: datetime) -> list[models.Transaction]:
    return (
        db.query(models.Transaction)
        .join(models.LinkedAccount)
        .filter(models.LinkedAccount.user_id == user_id)
        .filter(models.LinkedAccount.is_visible.is_(True))
        .filter(models.Transaction.booking_date >= start)
        .filter(models.Transaction.booking_date <= end)
        .all()
    )


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


def build_summary(db: Session, user_id: str, year: int, month: int) -> dict:
    # Una sola consulta para los 6 meses + el actual, agrupada en memoria por
    # (año, mes), en vez de una consulta de red separada por mes (7 antes)
    # -con una base de datos remota como Turso, cada consulta extra cuenta-.
    months = _previous_months(year, month, 6)
    range_start, _ = _month_bounds(*months[0])
    _, range_end = _month_bounds(*months[-1])
    all_transactions = _visible_transactions(db, user_id, range_start, range_end)

    by_month: dict[tuple[int, int], list[models.Transaction]] = {}
    for tx in all_transactions:
        by_month.setdefault((tx.booking_date.year, tx.booking_date.month), []).append(tx)

    current_month_transactions = by_month.get((year, month), [])
    internal_transfer_refs = detect_internal_transfers(current_month_transactions)

    income = expense = no_computable = 0.0
    spend_by_category: dict[str, float] = {}
    income_by_category: dict[str, float] = {}
    for tx in current_month_transactions:
        amount = abs(float(tx.amount))
        if tx.entry_reference in internal_transfer_refs:
            no_computable += amount
            continue
        if tx.credit_debit_indicator == "CRDT":
            income += amount
            if tx.category_id is not None:
                income_by_category[tx.category_id] = income_by_category.get(tx.category_id, 0) + amount
        else:
            expense += amount
            if tx.category_id is not None:
                spend_by_category[tx.category_id] = spend_by_category.get(tx.category_id, 0) + amount

    # El % de presupuesto solo tiene sentido comparando manzanas con manzanas:
    # el gasto SOLO de las categorias que tienen un limite puesto, contra la
    # suma de esos limites (antes se comparaba el gasto total del mes -todas
    # las categorias- contra la suma de unos pocos presupuestos, lo que
    # inflaba el % artificialmente si no todas las categorias tenian limite).
    #
    # El remanente (rollover) solo se aplica cuando se consulta el mes actual
    # de verdad: es un ajuste "de cara a este mes", no tiene sentido
    # recalcularlo para un mes ya cerrado del pasado.
    now = datetime.now(timezone.utc)
    budgets = db.query(models.Budget).join(models.Category).filter(models.Category.user_id == user_id).all()
    if (year, month) == (now.year, now.month):
        prev_spent_by_category = spent_by_category_previous_month(db, user_id)
        limits_by_category = {
            b.category_id: effective_limit(b, prev_spent_by_category.get(b.category_id, 0.0)) for b in budgets
        }
    else:
        limits_by_category = {b.category_id: float(b.monthly_limit) for b in budgets}

    budgeted_total = sum(limits_by_category.values())
    budgeted_expense = sum(spend_by_category.get(category_id, 0.0) for category_id in limits_by_category)
    budget_used_ratio = (budgeted_expense / budgeted_total) if budgeted_total > 0 else None

    last_six_months = []
    for y, m in months:
        month_income = month_expense = 0.0
        for tx in by_month.get((y, m), []):
            amount = abs(float(tx.amount))
            if tx.credit_debit_indicator == "CRDT":
                month_income += amount
            else:
                month_expense += amount
        last_six_months.append(
            {
                "month": f"{y:04d}-{m:02d}",
                "income": month_income,
                "expense": month_expense,
                "net": month_income - month_expense,
            }
        )

    categories = {c.id: c for c in db.query(models.Category).filter_by(user_id=user_id).all()}
    breakdown = [
        {"category": categories[category_id], "spent": spent}
        for category_id, spent in sorted(spend_by_category.items(), key=lambda kv: -kv[1])
        if category_id in categories
    ]
    income_breakdown = [
        {"category": categories[category_id], "spent": spent}
        for category_id, spent in sorted(income_by_category.items(), key=lambda kv: -kv[1])
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
        "income_breakdown": income_breakdown,
    }
