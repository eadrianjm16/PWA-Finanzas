import asyncio
import re

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import SessionLocal
from ..deps import CurrentUser, get_current_user, get_db_session
from ..services.enable_banking import EnableBankingClient, EnableBankingError
from ..services.sync import describe_enable_banking_error, refresh_balance

router = APIRouter(prefix="/api/accounts", tags=["accounts"])

_HEX_COLOR_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")


def _get_account_or_404(db: Session, user: CurrentUser, account_uid: str) -> models.LinkedAccount:
    account = db.query(models.LinkedAccount).filter_by(account_uid=account_uid, user_id=user.id).first()
    if account is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Cuenta no encontrada")
    return account


@router.get("", response_model=list[schemas.LinkedAccountOut])
def list_accounts(
    db: Session = Depends(get_db_session), user: CurrentUser = Depends(get_current_user)
) -> list[models.LinkedAccount]:
    return (
        db.query(models.LinkedAccount)
        .filter_by(user_id=user.id)
        .order_by(models.LinkedAccount.linked_at)
        .all()
    )


async def _refresh_one_balance_isolated(
    account_uid: str, user_id: str, client: EnableBankingClient
) -> schemas.SyncResult:
    # Sesion propia por cuenta (no la de la request): permite lanzar todas las
    # cuentas en paralelo con asyncio.gather sin que compartan una misma
    # Session de SQLAlchemy, que no soporta uso concurrente desde varias
    # tareas a la vez.
    session = SessionLocal()
    try:
        account = session.query(models.LinkedAccount).filter_by(account_uid=account_uid, user_id=user_id).first()
        if account is None:
            return schemas.SyncResult(account_uid=account_uid, ok=False, error="Cuenta no encontrada")
        try:
            await refresh_balance(session, account, client)
            return schemas.SyncResult(account_uid=account_uid, ok=True)
        except EnableBankingError as error:
            return schemas.SyncResult(account_uid=account_uid, ok=False, error=describe_enable_banking_error(error))
    finally:
        session.close()


@router.post("/refresh-all-balances", response_model=schemas.SyncResponse)
async def refresh_all_balances(
    request: Request, db: Session = Depends(get_db_session), user: CurrentUser = Depends(get_current_user)
) -> schemas.SyncResponse:
    client: EnableBankingClient = request.app.state.eb_client
    account_uids = [row[0] for row in db.query(models.LinkedAccount.account_uid).filter_by(user_id=user.id).all()]
    results = await asyncio.gather(
        *(_refresh_one_balance_isolated(account_uid, user.id, client) for account_uid in account_uids)
    )
    return schemas.SyncResponse(results=list(results), auto_categorized=[])


@router.patch("/{account_uid}", response_model=schemas.LinkedAccountOut)
def update_account(
    account_uid: str,
    payload: schemas.AccountUpdateRequest,
    db: Session = Depends(get_db_session),
    user: CurrentUser = Depends(get_current_user),
) -> models.LinkedAccount:
    account = _get_account_or_404(db, user, account_uid)
    if payload.display_name is not None:
        account.display_name = payload.display_name
    if payload.is_visible is not None:
        account.is_visible = payload.is_visible
    if payload.is_balance_visible is not None:
        account.is_balance_visible = payload.is_balance_visible
    if payload.color is not None:
        if not _HEX_COLOR_RE.match(payload.color):
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Color inválido, usa formato #RRGGBB")
        account.color = payload.color
    db.commit()
    db.refresh(account)
    return account


@router.post("/{account_uid}/refresh-balance", response_model=schemas.LinkedAccountOut)
async def refresh_account_balance(
    account_uid: str,
    request: Request,
    db: Session = Depends(get_db_session),
    user: CurrentUser = Depends(get_current_user),
) -> models.LinkedAccount:
    account = _get_account_or_404(db, user, account_uid)
    client: EnableBankingClient = request.app.state.eb_client
    try:
        await refresh_balance(db, account, client)
    except EnableBankingError as error:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, account.last_sync_issue or str(error)) from error
    db.refresh(account)
    return account
