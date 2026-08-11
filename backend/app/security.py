import hashlib
import time

import bcrypt
import jwt

from .config import settings

APP_TOKEN_TYPE = "session"
STATE_TOKEN_TYPE = "oauth_state"
RESET_TOKEN_TYPE = "password_reset"


def verify_password(plain_password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(plain_password.encode("utf-8"), password_hash.encode("utf-8"))


def hash_password(plain_password: str) -> str:
    return bcrypt.hashpw(plain_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def create_access_token(user_id: str, expires_minutes: int = 60 * 24 * 30) -> str:
    now = int(time.time())
    payload = {"type": APP_TOKEN_TYPE, "sub": user_id, "iat": now, "exp": now + expires_minutes * 60}
    return jwt.encode(payload, settings.app_jwt_secret, algorithm="HS256")


def decode_access_token(token: str) -> dict:
    payload = jwt.decode(token, settings.app_jwt_secret, algorithms=["HS256"])
    if payload.get("type") != APP_TOKEN_TYPE:
        raise jwt.InvalidTokenError("token type invalido")
    return payload


def create_oauth_state(user_id: str, aspsp_name: str, aspsp_country: str, expires_minutes: int = 15) -> str:
    """Firma el `state` que viaja ida y vuelta por el navegador durante la
    autorizacion PSD2. No necesitamos guardarlo en el servidor: el propio
    token, firmado, es la fuente de verdad al volver en /banks/callback. Lleva
    el user_id porque ese callback lo llama el banco sin Authorization header,
    asi que es la unica forma de saber a que usuario asignar la cuenta.
    """
    now = int(time.time())
    payload = {
        "type": STATE_TOKEN_TYPE,
        "user_id": user_id,
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


def _password_hash_fingerprint(password_hash: str) -> str:
    return hashlib.sha256(password_hash.encode("utf-8")).hexdigest()[:16]


def create_password_reset_token(user_id: str, current_password_hash: str, expires_minutes: int = 30) -> str:
    """El token lleva una huella del hash de contraseña actual: en cuanto la
    contraseña cambia (por este reset o por otro), la huella deja de coincidir
    y el token queda invalidado solo, sin necesidad de guardar nada en la
    base de datos ni llevar una lista de tokens usados.
    """
    now = int(time.time())
    payload = {
        "type": RESET_TOKEN_TYPE,
        "sub": user_id,
        "pwfp": _password_hash_fingerprint(current_password_hash),
        "iat": now,
        "exp": now + expires_minutes * 60,
    }
    return jwt.encode(payload, settings.app_jwt_secret, algorithm="HS256")


def decode_password_reset_token(token: str, current_password_hash: str) -> dict:
    payload = jwt.decode(token, settings.app_jwt_secret, algorithms=["HS256"])
    if payload.get("type") != RESET_TOKEN_TYPE:
        raise jwt.InvalidTokenError("token type invalido")
    if payload.get("pwfp") != _password_hash_fingerprint(current_password_hash):
        raise jwt.InvalidTokenError("Este enlace ya no es válido (la contraseña ya cambió)")
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
