from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app import models
from app.database import SessionLocal
from app.main import app
from tests.conftest import auth_headers, register_user


def _seed_transactions(user_id: str, count: int = 3) -> list[str]:
    db = SessionLocal()
    connection = models.BankConnection(user_id=user_id, key="Bulk Bank", aspsp_name="Bulk Bank", aspsp_country="ES")
    db.add(connection)
    db.flush()
    account = models.LinkedAccount(
        account_uid=f"acc-bulk-{user_id}", user_id=user_id, connection_id=connection.id, display_name="Cuenta"
    )
    db.add(account)
    refs = []
    for i in range(count):
        ref = f"bulk-tx-{i}-{user_id}"
        refs.append(ref)
        db.add(
            models.Transaction(
                entry_reference=ref,
                account_uid=account.account_uid,
                amount=10.0 + i,
                currency="EUR",
                credit_debit_indicator="DBIT",
                booking_date=datetime.now(timezone.utc),
                remittance_information=f"Movimiento {i}",
            )
        )
    db.commit()
    db.close()
    return refs


def _category_id_by_name(client, token, name: str) -> str:
    categories = client.get("/api/categories", headers=auth_headers(token)).json()
    return next(c["id"] for c in categories if c["name"] == name)


def test_bulk_categorize_updates_all_selected_transactions():
    with TestClient(app) as client:
        _, token = register_user(client)
        me = client.get("/api/auth/me", headers=auth_headers(token)).json()
        refs = _seed_transactions(me["id"], count=3)
        category_id = _category_id_by_name(client, token, "Ocio")

        response = client.patch(
            "/api/transactions/bulk-categorize",
            json={"entry_references": refs, "category_id": category_id},
            headers=auth_headers(token),
        )
        assert response.status_code == 200
        assert response.json()["updated_count"] == 3

        listed = client.get("/api/transactions", headers=auth_headers(token)).json()
        assert all(tx["category"]["id"] == category_id for tx in listed)
        assert all(tx["is_user_categorized"] for tx in listed)


def test_bulk_categorize_only_touches_own_transactions():
    with TestClient(app) as client:
        _, token_a = register_user(client)
        me_a = client.get("/api/auth/me", headers=auth_headers(token_a)).json()
        refs_a = _seed_transactions(me_a["id"], count=1)

        _, token_b = register_user(client)
        category_id_b = _category_id_by_name(client, token_b, "Ocio")

        response = client.patch(
            "/api/transactions/bulk-categorize",
            json={"entry_references": refs_a, "category_id": category_id_b},
            headers=auth_headers(token_b),
        )
        assert response.status_code == 200
        assert response.json()["updated_count"] == 0

        listed_a = client.get("/api/transactions", headers=auth_headers(token_a)).json()
        assert listed_a[0]["category"] is None


def test_bulk_categorize_rejects_unknown_category():
    with TestClient(app) as client:
        _, token = register_user(client)
        me = client.get("/api/auth/me", headers=auth_headers(token)).json()
        refs = _seed_transactions(me["id"], count=1)

        response = client.patch(
            "/api/transactions/bulk-categorize",
            json={"entry_references": refs, "category_id": "does-not-exist"},
            headers=auth_headers(token),
        )
    assert response.status_code == 404


def test_bulk_categorize_with_empty_list_is_a_noop():
    with TestClient(app) as client:
        _, token = register_user(client)
        category_id = _category_id_by_name(client, token, "Ocio")

        response = client.patch(
            "/api/transactions/bulk-categorize",
            json={"entry_references": [], "category_id": category_id},
            headers=auth_headers(token),
        )
    assert response.status_code == 200
    assert response.json()["updated_count"] == 0
