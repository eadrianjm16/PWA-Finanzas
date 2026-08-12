from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import models, schemas
from ..deps import CurrentUser, get_current_user, get_db_session

router = APIRouter(prefix="/api/loans", tags=["loans"])


def _get_loan_or_404(db: Session, user: CurrentUser, loan_id: str) -> models.Loan:
    loan = db.query(models.Loan).filter_by(id=loan_id, user_id=user.id).first()
    if loan is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Préstamo no encontrado")
    return loan


@router.get("", response_model=list[schemas.LoanOut])
def list_loans(
    db: Session = Depends(get_db_session), user: CurrentUser = Depends(get_current_user)
) -> list[models.Loan]:
    return db.query(models.Loan).filter_by(user_id=user.id).order_by(models.Loan.created_at).all()


@router.post("", response_model=schemas.LoanOut, status_code=status.HTTP_201_CREATED)
def create_loan(
    payload: schemas.LoanCreateRequest,
    db: Session = Depends(get_db_session),
    user: CurrentUser = Depends(get_current_user),
) -> models.Loan:
    if not payload.name.strip():
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "El nombre no puede estar vacío")
    if payload.balance < 0 or payload.monthly_payment < 0:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Los importes no pueden ser negativos")

    loan = models.Loan(
        user_id=user.id,
        name=payload.name.strip(),
        credit_limit=payload.credit_limit,
        balance=payload.balance,
        monthly_payment=payload.monthly_payment,
        tin=payload.tin,
        tae=payload.tae,
        next_payment_date=payload.next_payment_date,
    )
    db.add(loan)
    db.commit()
    db.refresh(loan)
    return loan


@router.patch("/{loan_id}", response_model=schemas.LoanOut)
def update_loan(
    loan_id: str,
    payload: schemas.LoanUpdateRequest,
    db: Session = Depends(get_db_session),
    user: CurrentUser = Depends(get_current_user),
) -> models.Loan:
    loan = _get_loan_or_404(db, user, loan_id)
    updates = payload.model_dump(exclude_unset=True)

    if "name" in updates and not updates["name"].strip():
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "El nombre no puede estar vacío")
    if updates.get("balance") is not None and updates["balance"] < 0:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "El saldo no puede ser negativo")
    if updates.get("monthly_payment") is not None and updates["monthly_payment"] < 0:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "La cuota no puede ser negativa")

    for field, value in updates.items():
        setattr(loan, field, value)
    if "name" in updates:
        loan.name = updates["name"].strip()

    db.commit()
    db.refresh(loan)
    return loan


@router.delete("/{loan_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_loan(
    loan_id: str, db: Session = Depends(get_db_session), user: CurrentUser = Depends(get_current_user)
) -> None:
    loan = _get_loan_or_404(db, user, loan_id)
    db.delete(loan)
    db.commit()
