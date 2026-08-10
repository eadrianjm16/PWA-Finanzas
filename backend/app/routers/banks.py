import jwt
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from .. import models, schemas
from ..config import settings
from ..deps import get_db_session, require_auth
from ..security import create_oauth_state, decode_oauth_state
from ..services.enable_banking import EnableBankingClient, EnableBankingError
from ..services.sync import link_accounts

router = APIRouter(prefix="/api/banks", tags=["banks"])


@router.get("/aspsps", response_model=list[schemas.ASPSPOut], dependencies=[Depends(require_auth)])
async def list_aspsps(request: Request, country: str | None = Query(default=None)) -> list[dict]:
    client: EnableBankingClient = request.app.state.eb_client
    try:
        return await client.list_aspsps(country)
    except EnableBankingError as error:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(error)) from error


@router.post(
    "/authorize", response_model=schemas.StartAuthorizationResponse, dependencies=[Depends(require_auth)]
)
async def start_authorization(payload: schemas.StartAuthorizationRequest, request: Request) -> schemas.StartAuthorizationResponse:
    client: EnableBankingClient = request.app.state.eb_client
    state = create_oauth_state(payload.aspsp.name, payload.aspsp.country)
    try:
        url = await client.start_authorization(
            aspsp=payload.aspsp.model_dump(exclude_none=True),
            state=state,
            redirect_url=settings.eb_redirect_url,
        )
    except EnableBankingError as error:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(error)) from error
    return schemas.StartAuthorizationResponse(url=url)


@router.get("/callback")
async def authorization_callback(
    request: Request,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    db: Session = Depends(get_db_session),
) -> RedirectResponse:
    """El navegador llega aqui redirigido por el banco tras el consentimiento
    PSD2 (redirect_url registrado en Enable Banking). No lleva Authorization
    header -no puede-, asi que la seguridad viene del `state` firmado por
    nosotros mismos: solo alguien que paso por /banks/authorize (autenticado)
    pudo generarlo, y caduca a los 15 minutos.
    """
    frontend_accounts_url = f"{settings.frontend_origin.rstrip('/')}/accounts"

    if error or not code or not state:
        return RedirectResponse(f"{frontend_accounts_url}?bank_error={error or 'missing_code'}")

    try:
        state_payload = decode_oauth_state(state)
    except jwt.PyJWTError:
        return RedirectResponse(f"{frontend_accounts_url}?bank_error=invalid_state")

    aspsp = {"name": state_payload["aspsp_name"], "country": state_payload["aspsp_country"]}
    client: EnableBankingClient = request.app.state.eb_client
    try:
        session_data = await client.create_session(code)
        link_accounts(db, session_data, aspsp)
    except EnableBankingError as api_error:
        return RedirectResponse(f"{frontend_accounts_url}?bank_error={api_error.status}")

    return RedirectResponse(f"{frontend_accounts_url}?connected=1")


@router.get(
    "/connections", response_model=list[schemas.BankConnectionOut], dependencies=[Depends(require_auth)]
)
def list_connections(db: Session = Depends(get_db_session)) -> list[models.BankConnection]:
    return db.query(models.BankConnection).order_by(models.BankConnection.linked_at).all()


@router.delete("/connections/{connection_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_auth)])
def delete_connection_route(connection_id: str, db: Session = Depends(get_db_session)) -> None:
    connection = db.get(models.BankConnection, connection_id)
    if connection is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Conexión no encontrada")
    db.delete(connection)
    db.commit()
