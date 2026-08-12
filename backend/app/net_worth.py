"""Historial de patrimonio neto (suma de saldos visibles). Sin cron en el
plan gratuito, se toma una foto (upsert por dia) cada vez que se listan las
conexiones bancarias en vez de en un job periodico."""

from datetime import date, timedelta

from sqlalchemy.orm import Session

from . import models

HISTORY_WINDOW_DAYS = 180


def snapshot_net_worth(db: Session, user_id: str) -> None:
    accounts = db.query(models.LinkedAccount).filter_by(user_id=user_id, is_visible=True).all()
    if not accounts or not any(a.last_balance_amount for a in accounts):
        return  # balances nunca actualizados: nada fiable que registrar todavia

    total = sum(float(a.last_balance_amount) for a in accounts if a.last_balance_amount)
    today = date.today().isoformat()

    existing = db.get(models.NetWorthSnapshot, (user_id, today))
    if existing is not None:
        existing.total_amount = total
    else:
        db.add(models.NetWorthSnapshot(user_id=user_id, date=today, total_amount=total))
    db.commit()


def net_worth_history(db: Session, user_id: str) -> list[dict]:
    since = (date.today() - timedelta(days=HISTORY_WINDOW_DAYS)).isoformat()
    rows = (
        db.query(models.NetWorthSnapshot)
        .filter_by(user_id=user_id)
        .filter(models.NetWorthSnapshot.date >= since)
        .order_by(models.NetWorthSnapshot.date)
        .all()
    )
    return [{"date": row.date, "total_amount": float(row.total_amount)} for row in rows]
