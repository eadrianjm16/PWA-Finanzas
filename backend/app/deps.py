import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from .database import get_db
from .security import decode_access_token

_bearer_scheme = HTTPBearer(auto_error=False)


def require_auth(credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme)) -> None:
    if credentials is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Falta el token de sesión")
    try:
        decode_access_token(credentials.credentials)
    except jwt.PyJWTError as error:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token de sesión inválido o caducado") from error


DbSession = Session
get_db_session = get_db
