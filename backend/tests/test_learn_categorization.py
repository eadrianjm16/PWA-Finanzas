from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app import models
from app.database import SessionLocal
from app.main import app
from tests.conftest import auth_headers, register_user


def _seed_transaction(user_id: str, entry_reference: str, counterparty_name: str) -> None:
    db = SessionLocal()
    connection = models.BankConnection(
        user_id=user_id, key=f"Learn Bank {entry_reference}", aspsp_name="Learn Bank", aspsp_country="ES"
    )
    db.add(connection)
    db.flush()
    account = models.LinkedAccount(
        account_uid=f"acc-learn-{entry_reference}", user_id=user_id, connection_id=connection.id, display_name="Cuenta"
    )
    db.add(account)
    db.add(
        models.Transaction(
            entry_reference=entry_reference,
            account_uid=account.account_uid,
            amount=12.0,
            currency="EUR",
            credit_debit_indicator="DBIT",
            booking_date=datetime.now(timezone.utc),
            remittance_information="",
            counterparty_name=counterparty_name,
        )
    )
    db.commit()
    db.close()


def _category_id_by_name(client, token, name: str) -> str:
    categories = client.get("/api/categories", headers=auth_headers(token)).json()
    return next(c["id"] for c in categories if c["name"] == name)


def test_categorizing_a_transaction_learns_a_rule():
    with TestClient(app) as client:
        _, token = register_user(client)
        me = client.get("/api/auth/me", headers=auth_headers(token)).json()
        _seed_transaction(me["id"], "learn-tx-1", "Netflix")
        category_id = _category_id_by_name(client, token, "Suscripciones")

        response = client.patch(
            "/api/transactions/learn-tx-1", json={"category_id": category_id}, headers=auth_headers(token)
        )
        assert response.status_code == 200

        rules = client.get("/api/categorization-rules", headers=auth_headers(token)).json()
    assert len(rules) == 1
    assert rules[0]["keyword"] == "Netflix"
    assert rules[0]["category"]["id"] == category_id


def test_categorizing_again_updates_the_learned_rule_instead_of_duplicating():
    with TestClient(app) as client:
        _, token = register_user(client)
        me = client.get("/api/auth/me", headers=auth_headers(token)).json()
        _seed_transaction(me["id"], "learn-tx-2a", "Netflix")
        _seed_transaction(me["id"], "learn-tx-2b", "Netflix")
        suscripciones = _category_id_by_name(client, token, "Suscripciones")
        ocio = _category_id_by_name(client, token, "Ocio")

        client.patch("/api/transactions/learn-tx-2a", json={"category_id": suscripciones}, headers=auth_headers(token))
        client.patch("/api/transactions/learn-tx-2b", json={"category_id": ocio}, headers=auth_headers(token))

        rules = client.get("/api/categorization-rules", headers=auth_headers(token)).json()
    netflix_rules = [r for r in rules if r["keyword"] == "Netflix"]
    assert len(netflix_rules) == 1
    assert netflix_rules[0]["category"]["id"] == ocio


def test_bulk_categorize_learns_a_rule_per_distinct_counterparty():
    with TestClient(app) as client:
        _, token = register_user(client)
        me = client.get("/api/auth/me", headers=auth_headers(token)).json()
        _seed_transaction(me["id"], "learn-tx-3a", "Spotify")
        _seed_transaction(me["id"], "learn-tx-3b", "Spotify")
        _seed_transaction(me["id"], "learn-tx-3c", "HBO Max")
        category_id = _category_id_by_name(client, token, "Suscripciones")

        client.patch(
            "/api/transactions/bulk-categorize",
            json={"entry_references": ["learn-tx-3a", "learn-tx-3b", "learn-tx-3c"], "category_id": category_id},
            headers=auth_headers(token),
        )

        rules = client.get("/api/categorization-rules", headers=auth_headers(token)).json()
    keywords = {r["keyword"] for r in rules}
    assert keywords == {"Spotify", "HBO Max"}
