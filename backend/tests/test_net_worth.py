from datetime import date

from fastapi.testclient import TestClient

from app import models
from app.database import SessionLocal
from app.main import app
from app.net_worth import net_worth_history, snapshot_net_worth
from tests.conftest import auth_headers, register_user


def _link_account_with_balance(user_id: str, balance: str) -> None:
    db = SessionLocal()
    connection = models.BankConnection(user_id=user_id, key=f"NW Bank {balance}", aspsp_name="NW Bank", aspsp_country="ES")
    db.add(connection)
    db.flush()
    db.add(
        models.LinkedAccount(
            account_uid=f"acc-nw-{user_id}-{balance}",
            user_id=user_id,
            connection_id=connection.id,
            display_name="Cuenta",
            last_balance_amount=balance,
            last_balance_currency="EUR",
        )
    )
    db.commit()
    db.close()


def test_snapshot_with_no_balances_yet_records_nothing():
    with TestClient(app) as client:
        _, token = register_user(client)
        me = client.get("/api/auth/me", headers=auth_headers(token)).json()

    db = SessionLocal()
    snapshot_net_worth(db, me["id"])
    history = net_worth_history(db, me["id"])
    db.close()
    assert history == []


def test_snapshot_records_todays_total():
    with TestClient(app) as client:
        _, token = register_user(client)
        me = client.get("/api/auth/me", headers=auth_headers(token)).json()

    _link_account_with_balance(me["id"], "1000.50")
    _link_account_with_balance(me["id"], "250.25")

    db = SessionLocal()
    snapshot_net_worth(db, me["id"])
    history = net_worth_history(db, me["id"])
    db.close()

    assert len(history) == 1
    assert history[0]["date"] == date.today().isoformat()
    assert history[0]["total_amount"] == 1250.75


def test_snapshot_twice_same_day_updates_instead_of_duplicating():
    with TestClient(app) as client:
        _, token = register_user(client)
        me = client.get("/api/auth/me", headers=auth_headers(token)).json()

    _link_account_with_balance(me["id"], "100.00")

    db = SessionLocal()
    snapshot_net_worth(db, me["id"])
    snapshot_net_worth(db, me["id"])
    history = net_worth_history(db, me["id"])
    db.close()

    assert len(history) == 1
    assert history[0]["total_amount"] == 100.00


def test_listing_bank_connections_takes_a_snapshot():
    with TestClient(app) as client:
        _, token = register_user(client)
        me = client.get("/api/auth/me", headers=auth_headers(token)).json()

    _link_account_with_balance(me["id"], "500.00")

    with TestClient(app) as client:
        client.get("/api/banks/connections", headers=auth_headers(token))
        history_response = client.get("/api/net-worth/history", headers=auth_headers(token))

    assert history_response.status_code == 200
    assert len(history_response.json()) == 1
    assert history_response.json()[0]["total_amount"] == 500.00
