from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session, joinedload, selectinload

from .. import models, schemas
from ..deps import CurrentUser, get_current_user, get_db_session
from ..services.enable_banking import EnableBankingClient, EnableBankingError
from ..services.push import notify_new_alerts
from ..services.sync import recategorize_uncategorized, sync_transactions

router = APIRouter(prefix="/api/transactions", tags=["transactions"])


def _get_transaction_or_404(db: Session, user: CurrentUser, entry_reference: str) -> models.Transaction:
    transaction = (
        db.query(models.Transaction)
        .join(models.LinkedAccount)
        .filter(models.LinkedAccount.user_id == user.id)
        .filter(models.Transaction.entry_reference == entry_reference)
        .first()
    )
    if transaction is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Movimiento no encontrado")
    return transaction


@router.get("", response_model=list[schemas.TransactionOut])
def list_transactions(
    account_uid: str | None = None,
    category_id: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    search: str | None = None,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db_session),
    user: CurrentUser = Depends(get_current_user),
) -> list[models.Transaction]:
    # category/debt_entries son lazy por defecto: sin eager loading, serializar
    # N movimientos dispara N consultas de red separadas a Turso (una por cada
    # `.has_debt_entries` accedido), en vez de una sola consulta con IN.
    query = (
        db.query(models.Transaction)
        .join(models.LinkedAccount)
        .filter(models.LinkedAccount.user_id == user.id)
        .options(
            joinedload(models.Transaction.category),
            selectinload(models.Transaction.debt_entries),
        )
    )
    if account_uid:
        query = query.filter(models.Transaction.account_uid == account_uid)
    if category_id:
        query = query.filter(models.Transaction.category_id == category_id)
    if date_from:
        query = query.filter(models.Transaction.booking_date >= date_from)
    if date_to:
        query = query.filter(models.Transaction.booking_date <= date_to)
    if search:
        pattern = f"%{search.strip()}%"
        query = query.filter(
            (models.Transaction.remittance_information.ilike(pattern))
            | (models.Transaction.counterparty_name.ilike(pattern))
        )
    return (
        query.order_by(models.Transaction.booking_date.desc())
        .limit(min(limit, 500))
        .offset(offset)
        .all()
    )


@router.patch("/{entry_reference}", response_model=schemas.TransactionOut)
def categorize_transaction(
    entry_reference: str,
    payload: schemas.TransactionCategorizeRequest,
    db: Session = Depends(get_db_session),
    user: CurrentUser = Depends(get_current_user),
) -> models.Transaction:
    transaction = _get_transaction_or_404(db, user, entry_reference)
    category = db.query(models.Category).filter_by(id=payload.category_id, user_id=user.id).first()
    if category is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Categoría no encontrada")
    transaction.category_id = category.id
    transaction.is_user_categorized = True
    db.commit()
    db.refresh(transaction)
    return transaction


@router.post("/sync", response_model=list[schemas.SyncResult])
async def sync_all(
    request: Request, db: Session = Depends(get_db_session), user: CurrentUser = Depends(get_current_user)
) -> list[schemas.SyncResult]:
    client: EnableBankingClient = request.app.state.eb_client
    results: list[schemas.SyncResult] = []
    for account in db.query(models.LinkedAccount).filter_by(user_id=user.id).all():
        try:
            await sync_transactions(db, account, client)
            results.append(schemas.SyncResult(account_uid=account.account_uid, ok=True))
        except EnableBankingError as error:
            results.append(schemas.SyncResult(account_uid=account.account_uid, ok=False, error=str(error)))

    notify_new_alerts(db, user.id)
    return results


@router.post("/recategorize-uncategorized", response_model=schemas.RecategorizeResult)
def recategorize(
    db: Session = Depends(get_db_session), user: CurrentUser = Depends(get_current_user)
) -> schemas.RecategorizeResult:
    return schemas.RecategorizeResult(updated_count=recategorize_uncategorized(db, user.id))


@router.post("/{entry_reference}/split", response_model=schemas.TransactionOut)
def split_transaction(
    entry_reference: str,
    payload: schemas.SplitTransactionRequest,
    db: Session = Depends(get_db_session),
    user: CurrentUser = Depends(get_current_user),
) -> models.Transaction:
    transaction = _get_transaction_or_404(db, user, entry_reference)
    if not payload.entries:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Selecciona al menos una persona")

    total = abs(float(transaction.amount))
    assigned = sum(entry.amount for entry in payload.entries)
    if any(entry.amount <= 0 for entry in payload.entries) or assigned <= 0 or assigned > total + 0.01:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Los importes no son válidos")

    note = transaction.counterparty_name or transaction.remittance_information
    for entry in payload.entries:
        debtor = db.query(models.Debtor).filter_by(id=entry.debtor_id, user_id=user.id).first()
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
