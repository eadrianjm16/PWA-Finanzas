from datetime import datetime, timezone

from app import models
from app.internal_transfers import detect


def _tx(entry_reference, account_uid, amount, credit_debit_indicator, day, currency="EUR"):
    return models.Transaction(
        entry_reference=entry_reference,
        account_uid=account_uid,
        amount=amount,
        currency=currency,
        credit_debit_indicator=credit_debit_indicator,
        booking_date=datetime(2026, 1, day, tzinfo=timezone.utc),
        remittance_information="",
    )


def test_matching_debit_and_credit_on_different_accounts_are_flagged():
    transactions = [
        _tx("a", "acc-santander", 100, "DBIT", day=10),
        _tx("b", "acc-ing", 100, "CRDT", day=11),
    ]
    assert detect(transactions) == {"a", "b"}


def test_same_account_pair_is_not_flagged():
    # Mismo importe pero misma cuenta -> no es un traspaso entre cuentas propias.
    transactions = [
        _tx("a", "acc-santander", 100, "DBIT", day=10),
        _tx("b", "acc-santander", 100, "CRDT", day=11),
    ]
    assert detect(transactions) == set()


def test_outside_time_window_is_not_flagged():
    transactions = [
        _tx("a", "acc-santander", 100, "DBIT", day=1),
        _tx("b", "acc-ing", 100, "CRDT", day=10),  # 9 dias despues, fuera de la ventana de 3
    ]
    assert detect(transactions) == set()


def test_two_debits_are_never_paired_as_a_transfer():
    transactions = [
        _tx("a", "acc-santander", 100, "DBIT", day=10),
        _tx("b", "acc-ing", 100, "DBIT", day=10),
    ]
    assert detect(transactions) == set()


def test_different_amounts_are_not_paired():
    transactions = [
        _tx("a", "acc-santander", 100, "DBIT", day=10),
        _tx("b", "acc-ing", 50, "CRDT", day=10),
    ]
    assert detect(transactions) == set()
