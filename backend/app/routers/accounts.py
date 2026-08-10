from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from .. import models, schemas
from ..deps import get_db_session, require_auth
from ..services.enable_banking import EnableBankingClient, EnableBankingError
from ..services.sync import refresh_balance

router = APIRouter(prefix="/api/accounts", tags=["accounts"], dependencies=[Depends(require_auth)])


def _get_account_or_404(db: Session, account_uid: str) -> models.LinkedAccount:
    account = db.get(models.LinkedAccount, account_uid)
    if account is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Cuenta no encontrada")
    return account


@router.get("", response_model=list[schemas.LinkedAccountOut])
def list_accounts(db: Session = Depends(get_db_session)) -> list[models.LinkedAccount]:
    return db.query(models.LinkedAccount).order_by(models.LinkedAccount.linked_at).all()


@router.patch("/{account_uid}", response_model=schemas.LinkedAccountOut)
def update_account(
    account_uid: str, payload: schemas.AccountUpdateRequest, db: Session = Depends(get_db_session)
) -> models.LinkedAccount:
    account = _get_account_or_404(db, account_uid)
    if payload.display_name is not None:
        account.display_name = payload.display_name
    if payload.is_visible is not None:
        account.is_visible = payload.is_visible
    if payload.is_balance_visible is not None:
        account.is_balance_visible = payload.is_balance_visible
    db.commit()
    db.refresh(account)
    return account


@router.post("/{account_uid}/refresh-balance", response_model=schemas.LinkedAccountOut)
async def refresh_account_balance(
    account_uid: str, request: Request, db: Session = Depends(get_db_session)
) -> models.LinkedAccount:
    account = _get_account_or_404(db, account_uid)
    client: EnableBankingClient = request.app.state.eb_client
    try:
        await refresh_balance(db, account, client)
    except EnableBankingError as error:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, account.last_sync_issue or str(error)) from error
    db.refresh(account)
    return account
