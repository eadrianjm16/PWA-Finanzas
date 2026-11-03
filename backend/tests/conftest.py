import os
import uuid
from pathlib import Path

import bcrypt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

TEST_PASSWORD = "test-password-123"
TEST_DB_PATH = Path(__file__).parent / "test_finanzas.db"


def _generate_test_rsa_pem() -> str:
    # Clave de usar-y-tirar, solo para que make_eb_application_token() (RS256)
    # tenga algo valido que firmar en los tests - el placeholder de texto
    # plano que habia antes nunca fue un PEM real, asi que cualquier test que
    # de verdad llamara a esa funcion habria fallado.
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()


os.environ.setdefault("EB_APPLICATION_ID", "test-application-id")
os.environ.setdefault("EB_PRIVATE_KEY_PEM", _generate_test_rsa_pem())
os.environ.setdefault("APP_JWT_SECRET", "test-jwt-secret")
os.environ.setdefault("APP_PASSWORD_HASH", bcrypt.hashpw(TEST_PASSWORD.encode(), bcrypt.gensalt()).decode())
os.environ.setdefault("DATABASE_URL", f"sqlite:///{TEST_DB_PATH}")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.rate_limit import limiter  # noqa: E402


@pytest.fixture(autouse=True, scope="session")
def _cleanup_test_db():
    yield
    TEST_DB_PATH.unlink(missing_ok=True)


@pytest.fixture(autouse=True)
def _reset_rate_limiter():
    # TestClient siempre usa la misma IP falsa: sin resetear, los contadores
    # de rate limit se acumulan entre tests en vez de aislarse por test.
    limiter.reset()
    yield


def register_user(client: TestClient, password: str = TEST_PASSWORD) -> tuple[str, str]:
    """Registra un usuario nuevo con email unico y devuelve (email, access_token)."""
    email = f"test-{uuid.uuid4()}@example.com"
    response = client.post("/api/auth/register", json={"email": email, "password": password})
    assert response.status_code == 201, response.text
    return email, response.json()["access_token"]


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}
