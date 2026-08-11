from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from .. import models, schemas
from ..default_categories import seed_categories_for_user
from ..deps import get_db_session
from ..rate_limit import limiter
from ..security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=schemas.TokenResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
def register(request: Request, payload: schemas.RegisterRequest, db: Session = Depends(get_db_session)) -> schemas.TokenResponse:
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
