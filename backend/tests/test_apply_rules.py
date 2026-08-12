import uuid
from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app import models
from app.database import SessionLocal
from app.main import app
from app.services.sync import apply_rules_to_all_matching
from tests.conftest import auth_headers, register_user


def _seed(user_id: str, entry_reference: str, remittance: str, is_user_categorized: bool = False):
    db = SessionLocal()
    connection = models.BankConnection(
        user_id=user_id, key=f"Bank {entry_reference}", aspsp_name="Test Bank", aspsp_country="ES"
    )
    db.add(connection)
    db.flush()
    account = models.LinkedAccount(
        account_uid=f"acc-{entry_reference}", user_id=user_id, connection_id=connection.id, display_name="Cuenta"
    )
    db.add(account)
    otros = db.query(models.Category).filter_by(user_id=user_id, name="Otros").first()
    db.add(
        models.Transaction(
            entry_reference=entry_reference,
            account_uid=account.account_uid,
            amount=-20,
            currency="EUR",
            credit_debit_indicator="DBIT",
            booking_date=datetime.now(timezone.utc),
            remittance_information=remittance,
            category_id=otros.id if otros else None,
            is_user_categorized=is_user_categorized,
        )
    )
    db.commit()
    db.close()


def test_apply_rules_overrides_a_manually_categorized_matching_transaction():
    with TestClient(app) as client:
        _, token = register_user(client)
        me = client.get("/api/auth/me", headers=auth_headers(token)).json()
        _seed(me["id"], f"apply-rules-tx1-{uuid.uuid4()}", "BIZUM DE JUAN PEREZ", is_user_categorized=True)

        categories = client.get("/api/categories", headers=auth_headers(token)).json()
        bizum_category = next(c for c in categories if c["name"] != "Otros")
        client.post(
            "/api/categorization-rules",
            json={"keyword": "BIZUM", "category_id": bizum_category["id"]},
            headers=auth_headers(token),
        )

        response = client.post("/api/transactions/apply-rules", headers=auth_headers(token))
        transactions = client.get("/api/transactions", headers=auth_headers(token)).json()

    assert response.status_code == 200
    assert response.json()["updated_count"] == 1
    assert transactions[0]["category"]["id"] == bizum_category["id"]


def test_apply_rules_leaves_non_matching_manual_categorization_untouched():
    with TestClient(app) as client:
        _, token = register_user(client)
        me = client.get("/api/auth/me", headers=auth_headers(token)).json()
        _seed(me["id"], f"apply-rules-tx2-{uuid.uuid4()}", "MERCADONA MADRID", is_user_categorized=True)

        categories = client.get("/api/categories", headers=auth_headers(token)).json()
        bizum_category = next(c for c in categories if c["name"] != "Otros")
        client.post(
            "/api/categorization-rules",
            json={"keyword": "BIZUM", "category_id": bizum_category["id"]},
            headers=auth_headers(token),
        )

        response = client.post("/api/transactions/apply-rules", headers=auth_headers(token))

    assert response.status_code == 200
    assert response.json()["updated_count"] == 0


def test_apply_rules_never_uses_the_automatic_suggestion_fallback():
    with TestClient(app) as client:
        _, token = register_user(client)
        me = client.get("/api/auth/me", headers=auth_headers(token)).json()
        _seed(me["id"], f"apply-rules-tx3-{uuid.uuid4()}", "NETFLIX SUSCRIPCION", is_user_categorized=True)
        # Sin ninguna regla creada: aunque suggest_category() probablemente
        # reconoceria "NETFLIX", apply_rules_to_all_matching no debe tocarlo -
        # solo obedece reglas explicitas, nunca la sugerencia automatica.
        db_session = SessionLocal()
        updated = apply_rules_to_all_matching(db_session, me["id"])
        db_session.close()

    assert updated == 0
