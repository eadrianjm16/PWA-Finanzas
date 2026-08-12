from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import models, schemas
from ..deps import CurrentUser, get_current_user, get_db_session
from ..recurring import detect_recurring_income

router = APIRouter(prefix="/api/fixed-expenses", tags=["fixed-expenses"])


def _current_month_key() -> str:
    return date.today().strftime("%Y-%m")


def _get_expense_or_404(db: Session, user: CurrentUser, expense_id: str) -> models.FixedExpense:
    expense = db.query(models.FixedExpense).filter_by(id=expense_id, user_id=user.id).first()
    if expense is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Gasto fijo no encontrado")
    return expense


@router.get("", response_model=list[schemas.FixedExpenseOut])
def list_fixed_expenses(
    month: str | None = None, db: Session = Depends(get_db_session), user: CurrentUser = Depends(get_current_user)
) -> list[dict]:
    month_key = month or _current_month_key()
    expenses = (
        db.query(models.FixedExpense).filter_by(user_id=user.id).order_by(models.FixedExpense.due_day).all()
    )
    checked_ids = {
        row[0]
        for row in db.query(models.FixedExpenseCheck.fixed_expense_id)
        .filter(models.FixedExpenseCheck.month_key == month_key)
        .filter(models.FixedExpenseCheck.fixed_expense_id.in_([e.id for e in expenses]))
        .all()
    }
    return [
        {
            "id": e.id,
            "name": e.name,
            "amount": float(e.amount),
            "due_day": e.due_day,
            "checked": e.id in checked_ids,
        }
        for e in expenses
    ]


@router.post("", response_model=schemas.FixedExpenseOut, status_code=status.HTTP_201_CREATED)
def create_fixed_expense(
    payload: schemas.FixedExpenseCreateRequest,
    db: Session = Depends(get_db_session),
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    if payload.amount <= 0:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "El importe debe ser mayor que 0")
    if not (1 <= payload.due_day <= 31):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "El día de vencimiento debe estar entre 1 y 31")

    expense = models.FixedExpense(
        user_id=user.id, name=payload.name.strip(), amount=payload.amount, due_day=payload.due_day
    )
    db.add(expense)
    db.commit()
    db.refresh(expense)
    return {"id": expense.id, "name": expense.name, "amount": float(expense.amount), "due_day": expense.due_day, "checked": False}


@router.patch("/{expense_id}", response_model=schemas.FixedExpenseOut)
def update_fixed_expense(
    expense_id: str,
    payload: schemas.FixedExpenseUpdateRequest,
    month: str | None = None,
    db: Session = Depends(get_db_session),
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    expense = _get_expense_or_404(db, user, expense_id)
    if payload.name is not None:
        expense.name = payload.name.strip()
    if payload.amount is not None:
        if payload.amount <= 0:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "El importe debe ser mayor que 0")
        expense.amount = payload.amount
    if payload.due_day is not None:
        if not (1 <= payload.due_day <= 31):
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "El día de vencimiento debe estar entre 1 y 31")
        expense.due_day = payload.due_day
    db.commit()

    month_key = month or _current_month_key()
    checked = db.get(models.FixedExpenseCheck, (expense.id, month_key)) is not None
    return {"id": expense.id, "name": expense.name, "amount": float(expense.amount), "due_day": expense.due_day, "checked": checked}


@router.delete("/{expense_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_fixed_expense(
    expense_id: str, db: Session = Depends(get_db_session), user: CurrentUser = Depends(get_current_user)
) -> None:
    expense = _get_expense_or_404(db, user, expense_id)
    db.delete(expense)
    db.commit()


@router.post("/{expense_id}/check", response_model=schemas.FixedExpenseOut)
def check_fixed_expense(
    expense_id: str,
    month: str | None = None,
    db: Session = Depends(get_db_session),
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    expense = _get_expense_or_404(db, user, expense_id)
    month_key = month or _current_month_key()
    if db.get(models.FixedExpenseCheck, (expense.id, month_key)) is None:
        db.add(models.FixedExpenseCheck(fixed_expense_id=expense.id, month_key=month_key))
        db.commit()
    return {"id": expense.id, "name": expense.name, "amount": float(expense.amount), "due_day": expense.due_day, "checked": True}


@router.delete("/{expense_id}/check", response_model=schemas.FixedExpenseOut)
def uncheck_fixed_expense(
    expense_id: str,
    month: str | None = None,
    db: Session = Depends(get_db_session),
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    expense = _get_expense_or_404(db, user, expense_id)
    month_key = month or _current_month_key()
    check = db.get(models.FixedExpenseCheck, (expense.id, month_key))
    if check is not None:
        db.delete(check)
        db.commit()
    return {"id": expense.id, "name": expense.name, "amount": float(expense.amount), "due_day": expense.due_day, "checked": False}


@router.get("/summary", response_model=schemas.FixedExpensesSummaryOut)
def fixed_expenses_summary(
    db: Session = Depends(get_db_session), user: CurrentUser = Depends(get_current_user)
) -> schemas.FixedExpensesSummaryOut:
    total_fixed = sum(
        float(e.amount) for e in db.query(models.FixedExpense).filter_by(user_id=user.id).all()
    )

    override = db.get(models.IncomeOverride, user.id)
    if override is not None:
        income = float(override.monthly_amount)
        is_manual = True
    else:
        detected = detect_recurring_income(db, user.id)
        income = detected["amount"] if detected else None
        is_manual = False

    leftover = (income - total_fixed) if income is not None else None
    return schemas.FixedExpensesSummaryOut(
        estimated_income=income, income_is_manual=is_manual, total_fixed=total_fixed, estimated_leftover=leftover
    )


@router.put("/income-override", response_model=schemas.FixedExpensesSummaryOut)
def set_income_override(
    payload: schemas.IncomeOverrideRequest,
    db: Session = Depends(get_db_session),
    user: CurrentUser = Depends(get_current_user),
) -> schemas.FixedExpensesSummaryOut:
    existing = db.get(models.IncomeOverride, user.id)
    if payload.monthly_amount is None:
        if existing is not None:
            db.delete(existing)
            db.commit()
    else:
        if payload.monthly_amount <= 0:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "La nómina debe ser mayor que 0")
        if existing is None:
            db.add(models.IncomeOverride(user_id=user.id, monthly_amount=payload.monthly_amount))
        else:
            existing.monthly_amount = payload.monthly_amount
        db.commit()

    return fixed_expenses_summary(db, user)
