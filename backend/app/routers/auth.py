from fastapi import APIRouter, HTTPException, status

from .. import schemas
from ..security import create_access_token, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=schemas.TokenResponse)
def login(payload: schemas.LoginRequest) -> schemas.TokenResponse:
    if not verify_password(payload.password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Contraseña incorrecta")
    return schemas.TokenResponse(access_token=create_access_token())
