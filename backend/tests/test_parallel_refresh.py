"""Las cuentas de un usuario se refrescan en paralelo (asyncio.gather), no una
a una: con varios bancos conectados, el tiempo total deja de ser la suma de
cada llamada a Enable Banking y pasa a ser, aproximadamente, la de la mas
lenta. Estos tests simulan la latencia de red y verifican el tiempo total en
vez de limitarse a comprobar el resultado."""

import asyncio
import time
import uuid

import pytest
from sqlalchemy.orm import Session

from app import models
from app.database import SessionLocal, engine
from app.routers.accounts import _refresh_one_balance_isolated
from app.routers.transactions import _sync_one_account_isolated

ACCOUNT_COUNT = 3
DELAY_SECONDS = 0.2


@pytest.fixture
def db():
    models.Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture
def accounts(db: Session) -> list[models.LinkedAccount]:
    user = models.User(email=f"parallel-{uuid.uuid4()}@example.com", password_hash="x")
    db.add(user)
    db.flush()
    db.add(models.Category(user_id=user.id, name="Otros", system_icon_name="help-circle", sort_order=0))

    created = []
    for i in range(ACCOUNT_COUNT):
        connection = models.BankConnection(
            user_id=user.id, key=f"Test Bank {i}|ES", aspsp_name=f"Test Bank {i}", aspsp_country="ES"
        )
        db.add(connection)
        db.flush()
        account = models.LinkedAccount(
            account_uid=f"acc-{uuid.uuid4()}",
            user_id=user.id,
            connection_id=connection.id,
            display_name=f"Cuenta {i}",
        )
        db.add(account)
        created.append(account)
    db.commit()
    return created


class SlowFakeClient:
    """Cada llamada simula una latencia de red fija (DELAY_SECONDS)."""

    async def fetch_balances(self, account_uid: str) -> list[dict]:
        await asyncio.sleep(DELAY_SECONDS)
        return [{"balance_type": "CLBD", "balance_amount": {"amount": "100.00", "currency": "EUR"}}]

    async def fetch_all_transactions(self, account_uid: str, date_from=None, date_to=None) -> list[dict]:
        await asyncio.sleep(DELAY_SECONDS)
        return []


async def test_refresh_all_balances_runs_accounts_in_parallel(accounts):
    client = SlowFakeClient()
    user_id = accounts[0].user_id

    start = time.monotonic()
    results = await asyncio.gather(
        *(_refresh_one_balance_isolated(account.account_uid, user_id, client) for account in accounts)
    )
    elapsed = time.monotonic() - start

    assert all(r.ok for r in results)
    # Secuencial tardaria ~ACCOUNT_COUNT * DELAY_SECONDS; en paralelo, ~1 * DELAY_SECONDS.
    assert elapsed < DELAY_SECONDS * (ACCOUNT_COUNT - 1)


async def test_sync_all_runs_accounts_in_parallel(accounts):
    client = SlowFakeClient()
    user_id = accounts[0].user_id

    start = time.monotonic()
    outcomes = await asyncio.gather(
        *(_sync_one_account_isolated(account.account_uid, user_id, client) for account in accounts)
    )
    elapsed = time.monotonic() - start

    assert all(result.ok for result, _ in outcomes)
    assert elapsed < DELAY_SECONDS * (ACCOUNT_COUNT - 1)
