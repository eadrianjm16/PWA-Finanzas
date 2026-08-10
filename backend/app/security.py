import time

import bcrypt
import jwt

from .config import settings

APP_TOKEN_TYPE = "session"
STATE_TOKEN_TYPE = "oauth_state"


def verify_password(plain_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode("utf-8"), settings.app_password_hash.encode("utf-8"))


def hash_password(plain_password: str) -> str:
    return bcrypt.hashpw(plain_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def create_access_token(expires_minutes: int = 60 * 24 * 30) -> str:
    now = int(time.time())
    payload = {"type": APP_TOKEN_TYPE, "iat": now, "exp": now + expires_minutes * 60}
    return jwt.encode(payload, settings.app_jwt_secret, algorithm="HS256")


def decode_access_token(token: str) -> dict:
    payload = jwt.decode(token, settings.app_jwt_secret, algorithms=["HS256"])
    if payload.get("type") != APP_TOKEN_TYPE:
        raise jwt.InvalidTokenError("token type invalido")
    return payload


def create_oauth_state(aspsp_name: str, aspsp_country: str, expires_minutes: int = 15) -> str:
    """Firma el `state` que viaja ida y vuelta por el navegador durante la
    autorizacion PSD2. No necesitamos guardarlo en el servidor: el propio
    token, firmado, es la fuente de verdad al volver en /banks/callback.
    """
    now = int(time.time())
    payload = {
        "type": STATE_TOKEN_TYPE,
        "aspsp_name": aspsp_name,
        "aspsp_country": aspsp_country,
        "iat": now,
        "exp": now + expires_minutes * 60,
    }
    return jwt.encode(payload, settings.app_jwt_secret, algorithm="HS256")


def decode_oauth_state(token: str) -> dict:
    payload = jwt.decode(token, settings.app_jwt_secret, algorithms=["HS256"])
    if payload.get("type") != STATE_TOKEN_TYPE:
        raise jwt.InvalidTokenError("token type invalido")
    return payload


def make_eb_application_token() -> str:
    """JWT (RS256, firmado con la clave privada de la app) que Enable Banking
    exige en cada peticion. Equivalente a JWTSigner.makeApplicationToken()
    de la app iOS, pero mucho mas simple: PyJWT acepta PEM PKCS#1 y PKCS#8
    directamente, sin necesidad de desempaquetar el DER a mano.
    """
    now = int(time.time())
    payload = {"iss": "enablebanking.com", "aud": "api.enablebanking.com", "iat": now, "exp": now + 3600}
    headers = {"kid": settings.eb_application_id}
    return jwt.encode(payload, settings.eb_private_key_pem, algorithm="RS256", headers=headers)
