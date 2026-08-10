from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from .. import models, schemas
from ..deps import get_db_session, require_auth
from ..services.enable_banking import EnableBankingClient, EnableBankingError
from ..services.sync import recategorize_uncategorized, sync_transactions

router = APIRouter(prefix="/api/transactions", tags=["transactions"], dependencies=[Depends(require_auth)])


@router.get("", response_model=list[schemas.TransactionOut])
def list_transactions(
    account_uid: str | None = None,
    category_id: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db_session),
) -> list[models.Transaction]:
    query = db.query(models.Transaction)
    if account_uid:
        query = query.filter(models.Transaction.account_uid == account_uid)
    if category_id:
        query = query.filter(models.Transaction.category_id == category_id)
    if date_from:
        query = query.filter(models.Transaction.booking_date >= date_from)
    if date_to:
        query = query.filter(models.Transaction.booking_date <= date_to)
    return (
        query.order_by(models.Transaction.booking_date.desc())
        .limit(min(limit, 500))
        .offset(offset)
        .all()
    )


@router.patch("/{entry_reference}", response_model=schemas.TransactionOut)
def categorize_transaction(
    entry_reference: str, payload: schemas.TransactionCategorizeRequest, db: Session = Depends(get_db_session)
) -> models.Transaction:
    transaction = db.get(models.Transaction, entry_reference)
    if transaction is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Movimiento no encontrado")
    category = db.get(models.Category, payload.category_id)
    if category is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Categoría no encontrada")
    transaction.category_id = category.id
    transaction.is_user_categorized = True
    db.commit()
    db.refresh(transaction)
    return transaction


@router.post("/sync", response_model=list[schemas.SyncResult])
async def sync_all(request: Request, db: Session = Depends(get_db_session)) -> list[schemas.SyncResult]:
    client: EnableBankingClient = request.app.state.eb_client
    results: list[schemas.SyncResult] = []
    for account in db.query(models.LinkedAccount).all():
        try:
            await sync_transactions(db, account, client)
            results.append(schemas.SyncResult(account_uid=account.account_uid, ok=True))
        except EnableBankingError as error:
            results.append(schemas.SyncResult(account_uid=account.account_uid, ok=False, error=str(error)))
    return results


@router.post("/recategorize-uncategorized", response_model=schemas.RecategorizeResult)
def recategorize(db: Session = Depends(get_db_session)) -> schemas.RecategorizeResult:
    return schemas.RecategorizeResult(updated_count=recategorize_uncategorized(db))


@router.post("/{entry_reference}/split", response_model=schemas.TransactionOut)
def split_transaction(
    entry_reference: str, payload: schemas.SplitTransactionRequest, db: Session = Depends(get_db_session)
) -> models.Transaction:
    transaction = db.get(models.Transaction, entry_reference)
    if transaction is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Movimiento no encontrado")
    if not payload.entries:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Selecciona al menos una persona")

    total = abs(float(transaction.amount))
    assigned = sum(entry.amount for entry in payload.entries)
    if any(entry.amount <= 0 for entry in payload.entries) or assigned <= 0 or assigned > total + 0.01:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Los importes no son válidos")

    note = transaction.counterparty_name or transaction.remittance_information
    for entry in payload.entries:
        debtor = db.get(models.Debtor, entry.debtor_id)
        if debtor is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, f"Deudor no encontrado: {entry.debtor_id}")
        db.add(
            models.DebtEntry(
                debtor_id=debtor.id,
                amount=entry.amount,
                date=transaction.booking_date,
                note=note,
                transaction_entry_reference=transaction.entry_reference,
            )
        )

    db.commit()
    db.refresh(transaction)
    return transaction
