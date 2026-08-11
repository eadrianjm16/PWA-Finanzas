import os
from pathlib import Path

import bcrypt

TEST_PASSWORD = "test-password-123"
TEST_DB_PATH = Path(__file__).parent / "test_finanzas.db"

os.environ.setdefault("EB_APPLICATION_ID", "test-application-id")
os.environ.setdefault(
    "EB_PRIVATE_KEY_PEM", "-----BEGIN PRIVATE KEY-----\ntest-key-not-real\n-----END PRIVATE KEY-----"
)
os.environ.setdefault("APP_JWT_SECRET", "test-jwt-secret")
os.environ.setdefault("APP_PASSWORD_HASH", bcrypt.hashpw(TEST_PASSWORD.encode(), bcrypt.gensalt()).decode())
os.environ.setdefault("DATABASE_URL", f"sqlite:///{TEST_DB_PATH}")

import pytest  # noqa: E402


@pytest.fixture(autouse=True, scope="session")
def _cleanup_test_db():
    yield
    TEST_DB_PATH.unlink(missing_ok=True)
