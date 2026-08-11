import jwt
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from .. import models, schemas
from ..config import settings
from ..default_categories import seed_categories_for_user
from ..deps import get_db_session
from ..rate_limit import limiter
from ..security import (
    create_access_token,
    create_password_reset_token,
    decode_password_reset_token,
    hash_password,
    verify_password,
)
from ..services.email import send_password_reset_email

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=schemas.TokenResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
def register(request: Request, payload: schemas.RegisterRequest, db: Session = Depends(get_db_session)) -> schemas.TokenResponse:
    if settings.registration_invite_code and payload.invite_code != settings.registration_invite_code:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Código de invitación incorrecto")

    email = payload.email.strip().lower()
    if db.query(models.User).filter_by(email=email).first() is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Ya existe una cuenta con ese email")
    if len(payload.password) < 8:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "La contraseña debe tener al menos 8 caracteres")

    user = models.User(email=email, password_hash=hash_password(payload.password))
    db.add(user)
    db.commit()
    db.refresh(user)

    seed_categories_for_user(db, user.id)

    return schemas.TokenResponse(access_token=create_access_token(user.id))


@router.post("/login", response_model=schemas.TokenResponse)
@limiter.limit("5/minute")
def login(request: Request, payload: schemas.LoginRequest, db: Session = Depends(get_db_session)) -> schemas.TokenResponse:
    email = payload.email.strip().lower()
    user = db.query(models.User).filter_by(email=email).first()
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Email o contraseña incorrectos")
    return schemas.TokenResponse(access_token=create_access_token(user.id))


@router.post("/forgot-password", response_model=schemas.MessageResponse)
@limiter.limit("5/minute")
async def forgot_password(
    request: Request, payload: schemas.ForgotPasswordRequest, db: Session = Depends(get_db_session)
) -> schemas.MessageResponse:
    generic_message = "Si existe una cuenta con ese email, te hemos enviado un enlace para restablecer la contraseña."

    email = payload.email.strip().lower()
    user = db.query(models.User).filter_by(email=email).first()
    if user is not None:
        token = create_password_reset_token(user.id, user.password_hash)
        reset_url = f"{settings.frontend_origin.rstrip('/')}/reset-password?token={token}"
        await send_password_reset_email(user.email, reset_url)

    # Mismo mensaje exista o no la cuenta: evita que alguien use este
    # endpoint para averiguar que emails estan registrados.
    return schemas.MessageResponse(message=generic_message)


@router.post("/reset-password", response_model=schemas.MessageResponse)
@limiter.limit("5/minute")
def reset_password(
    request: Request, payload: schemas.ResetPasswordRequest, db: Session = Depends(get_db_session)
) -> schemas.MessageResponse:
    if len(payload.new_password) < 8:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "La contraseña debe tener al menos 8 caracteres")

    try:
        unverified = jwt.decode(payload.token, options={"verify_signature": False})
    except jwt.PyJWTError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Enlace inválido o caducado")

    user = db.get(models.User, unverified.get("sub"))
    if user is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Enlace inválido o caducado")

    try:
        decode_password_reset_token(payload.token, user.password_hash)
    except jwt.PyJWTError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Enlace inválido o caducado")

    user.password_hash = hash_password(payload.new_password)
    db.commit()
    return schemas.MessageResponse(message="Contraseña actualizada. Ya puedes entrar con la nueva.")
