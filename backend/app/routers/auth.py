from fastapi import APIRouter, HTTPException, Request, status

from .. import schemas
from ..rate_limit import limiter
from ..security import create_access_token, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=schemas.TokenResponse)
@limiter.limit("5/minute")
def login(request: Request, payload: schemas.LoginRequest) -> schemas.TokenResponse:
    if not verify_password(payload.password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Contraseña incorrecta")
    return schemas.TokenResponse(access_token=create_access_token())
