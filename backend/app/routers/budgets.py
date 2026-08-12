from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from .. import models, schemas
from ..budget_calc import effective_limit as _effective_limit
from ..budget_calc import spent_by_category_previous_month as _spent_by_category_previous_month
from ..deps import CurrentUser, get_current_user, get_db_session

router = APIRouter(prefix="/api/budgets", tags=["budgets"])


def _spent_this_month(db: Session, user: CurrentUser, category_id: str) -> float:
    start = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    transactions = (
        db.query(models.Transaction)
        .join(models.LinkedAccount)
        .filter(models.LinkedAccount.user_id == user.id)
        .filter(models.LinkedAccount.is_visible.is_(True))
        .filter(models.Transaction.category_id == category_id)
        .filter(models.Transaction.credit_debit_indicator == "DBIT")
        .filter(models.Transaction.booking_date >= start)
        .all()
    )
    return sum(abs(float(tx.amount)) for tx in transactions)


def _spent_by_category_this_month(db: Session, user: CurrentUser) -> dict[str, float]:
    """Version agrupada de _spent_this_month para el listado: una sola
    consulta con GROUP BY en vez de una consulta por categoria (con una base
    de datos remota como Turso, cada consulta extra es un round-trip de red)."""
    start = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    rows = (
        db.query(models.Transaction.category_id, func.sum(models.Transaction.amount))
        .join(models.LinkedAccount)
        .filter(models.LinkedAccount.user_id == user.id)
        .filter(models.LinkedAccount.is_visible.is_(True))
        .filter(models.Transaction.credit_debit_indicator == "DBIT")
        .filter(models.Transaction.booking_date >= start)
        .group_by(models.Transaction.category_id)
        .all()
    )
    return {category_id: abs(float(total)) for category_id, total in rows if category_id is not None}


@router.get("", response_model=list[schemas.BudgetOut])
def list_budgets(
    db: Session = Depends(get_db_session), user: CurrentUser = Depends(get_current_user)
) -> list[schemas.BudgetOut]:
    categories = db.query(models.Category).filter_by(user_id=user.id).order_by(models.Category.sort_order).all()
    budgets_by_category = {
        b.category_id: b
        for b in db.query(models.Budget).join(models.Category).filter(models.Category.user_id == user.id).all()
    }
    spent_by_category = _spent_by_category_this_month(db, user)
    prev_spent_by_category = _spent_by_category_previous_month(db, user.id)
    return [
        schemas.BudgetOut(
            category=category,
            monthly_limit=(
                float(budgets_by_category[category.id].monthly_limit)
                if category.id in budgets_by_category
                else None
            ),
            effective_limit=_effective_limit(
                budgets_by_category.get(category.id), prev_spent_by_category.get(category.id, 0.0)
            ),
            rollover=budgets_by_category.get(category.id).rollover if category.id in budgets_by_category else False,
            spent_this_month=spent_by_category.get(category.id, 0.0),
        )
        for category in categories
    ]


@router.put("/{category_id}", response_model=schemas.BudgetOut)
def upsert_budget(
    category_id: str,
    payload: schemas.BudgetUpsertRequest,
    db: Session = Depends(get_db_session),
    user: CurrentUser = Depends(get_current_user),
) -> schemas.BudgetOut:
    category = db.query(models.Category).filter_by(id=category_id, user_id=user.id).first()
    if category is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Categoría no encontrada")

    budget = db.get(models.Budget, category_id)
    if budget is None:
        budget = models.Budget(category_id=category_id, monthly_limit=payload.monthly_limit, rollover=payload.rollover)
        db.add(budget)
    else:
        budget.monthly_limit = payload.monthly_limit
        budget.rollover = payload.rollover
    db.commit()

    prev_spent = _spent_by_category_previous_month(db, user.id).get(category_id, 0.0)
    return schemas.BudgetOut(
        category=category,
        monthly_limit=float(payload.monthly_limit),
        effective_limit=_effective_limit(budget, prev_spent),
        rollover=budget.rollover,
        spent_this_month=_spent_this_month(db, user, category_id),
    )


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_budget(
    category_id: str, db: Session = Depends(get_db_session), user: CurrentUser = Depends(get_current_user)
) -> None:
    category = db.query(models.Category).filter_by(id=category_id, user_id=user.id).first()
    if category is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Categoría no encontrada")
    budget = db.get(models.Budget, category_id)
    if budget is not None:
        db.delete(budget)
        db.commit()
