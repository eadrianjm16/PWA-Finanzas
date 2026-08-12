"""Calculo compartido del limite efectivo de un presupuesto (con remanente
opcional del mes anterior). Vive fuera de routers/budgets.py para que
analysis.py tambien pueda usarlo sin que un modulo de logica de negocio
dependa de un router."""

from datetime import datetime, timedelta, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from . import models


def spent_by_category_previous_month(db: Session, user_id: str) -> dict[str, float]:
    now = datetime.now(timezone.utc)
    this_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    prev_month_start = (this_month_start - timedelta(days=1)).replace(day=1)
    rows = (
        db.query(models.Transaction.category_id, func.sum(models.Transaction.amount))
        .join(models.LinkedAccount)
        .filter(models.LinkedAccount.user_id == user_id)
        .filter(models.LinkedAccount.is_visible.is_(True))
        .filter(models.Transaction.credit_debit_indicator == "DBIT")
        .filter(models.Transaction.booking_date >= prev_month_start)
        .filter(models.Transaction.booking_date < this_month_start)
        .group_by(models.Transaction.category_id)
        .all()
    )
    return {category_id: abs(float(total)) for category_id, total in rows if category_id is not None}


def effective_limit(budget: "models.Budget | None", prev_spent: float) -> float | None:
    """Con rollover activo, el limite efectivo de este mes suma lo que sobro
    el mes pasado (monthly_limit - lo gastado entonces, sin bajar de 0). Solo
    mira un mes atras -no se acumula sin limite mes a mes- para mantenerlo
    simple y predecible."""
    if budget is None:
        return None
    limit = float(budget.monthly_limit)
    if not budget.rollover:
        return limit
    leftover = max(0.0, limit - prev_spent)
    return limit + leftover
