import jwt
import pytest

from app.security import (
    create_access_token,
    create_oauth_state,
    decode_access_token,
    decode_oauth_state,
    hash_password,
    verify_password,
)


def test_hash_password_produces_a_bcrypt_hash_distinct_from_the_input():
    hashed = hash_password("my-secret")
    assert hashed != "my-secret"
    assert hashed.startswith("$2b$")


def test_verify_password_against_configured_hash():
    from tests.conftest import TEST_PASSWORD

    assert verify_password(TEST_PASSWORD) is True
    assert verify_password("wrong-password") is False


def test_access_token_roundtrip():
    token = create_access_token()
    payload = decode_access_token(token)
    assert payload["type"] == "session"


def test_access_token_rejects_garbage():
    with pytest.raises(jwt.PyJWTError):
        decode_access_token("not-a-real-token")


def test_oauth_state_roundtrip():
    token = create_oauth_state("Banco Santander", "ES")
    payload = decode_oauth_state(token)
    assert payload["aspsp_name"] == "Banco Santander"
    assert payload["aspsp_country"] == "ES"
    assert payload["type"] == "oauth_state"


def test_oauth_state_cannot_be_used_as_access_token():
    state_token = create_oauth_state("Banco Santander", "ES")
    with pytest.raises(jwt.InvalidTokenError):
        decode_access_token(state_token)
