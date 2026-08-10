from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import models, schemas
from ..deps import get_db_session, require_auth

router = APIRouter(prefix="/api/budgets", tags=["budgets"], dependencies=[Depends(require_auth)])


def _spent_this_month(db: Session, category_id: str) -> float:
    start = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    transactions = (
        db.query(models.Transaction)
        .join(models.LinkedAccount)
        .filter(models.LinkedAccount.is_visible.is_(True))
        .filter(models.Transaction.category_id == category_id)
        .filter(models.Transaction.credit_debit_indicator == "DBIT")
        .filter(models.Transaction.booking_date >= start)
        .all()
    )
    return sum(abs(float(tx.amount)) for tx in transactions)


@router.get("", response_model=list[schemas.BudgetOut])
def list_budgets(db: Session = Depends(get_db_session)) -> list[schemas.BudgetOut]:
    categories = db.query(models.Category).order_by(models.Category.sort_order).all()
    budgets_by_category = {b.category_id: b for b in db.query(models.Budget).all()}
    return [
        schemas.BudgetOut(
            category=category,
            monthly_limit=(
                float(budgets_by_category[category.id].monthly_limit)
                if category.id in budgets_by_category
                else None
            ),
            spent_this_month=_spent_this_month(db, category.id),
        )
        for category in categories
    ]


@router.put("/{category_id}", response_model=schemas.BudgetOut)
def upsert_budget(
    category_id: str, payload: schemas.BudgetUpsertRequest, db: Session = Depends(get_db_session)
) -> schemas.BudgetOut:
    category = db.get(models.Category, category_id)
    if category is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Categoría no encontrada")

    budget = db.get(models.Budget, category_id)
    if budget is None:
        budget = models.Budget(category_id=category_id, monthly_limit=payload.monthly_limit)
        db.add(budget)
    else:
        budget.monthly_limit = payload.monthly_limit
    db.commit()

    return schemas.BudgetOut(
        category=category,
        monthly_limit=float(payload.monthly_limit),
        spent_this_month=_spent_this_month(db, category_id),
    )


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_budget(category_id: str, db: Session = Depends(get_db_session)) -> None:
    budget = db.get(models.Budget, category_id)
    if budget is not None:
        db.delete(budget)
        db.commit()
