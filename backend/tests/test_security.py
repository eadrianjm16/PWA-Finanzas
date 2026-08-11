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


def test_verify_password_against_its_own_hash():
    hashed = hash_password("correct horse battery staple")
    assert verify_password("correct horse battery staple", hashed) is True
    assert verify_password("wrong-password", hashed) is False


def test_access_token_roundtrip():
    token = create_access_token("user-123")
    payload = decode_access_token(token)
    assert payload["type"] == "session"
    assert payload["sub"] == "user-123"


def test_access_token_rejects_garbage():
    with pytest.raises(jwt.PyJWTError):
        decode_access_token("not-a-real-token")


def test_oauth_state_roundtrip():
    token = create_oauth_state("user-123", "Banco Santander", "ES")
    payload = decode_oauth_state(token)
    assert payload["user_id"] == "user-123"
    assert payload["aspsp_name"] == "Banco Santander"
    assert payload["aspsp_country"] == "ES"
    assert payload["type"] == "oauth_state"


def test_oauth_state_cannot_be_used_as_access_token():
    state_token = create_oauth_state("user-123", "Banco Santander", "ES")
    with pytest.raises(jwt.InvalidTokenError):
        decode_access_token(state_token)
