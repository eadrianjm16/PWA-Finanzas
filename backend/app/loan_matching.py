"""Relaciona un préstamo (seguimiento manual, ver models.Loan) con el cargo
real que le corresponde en Movimientos, para que el usuario no tenga que
comprobarlo a mano: busca, entre los movimientos sincronizados del banco, uno
cuyo concepto mencione el nombre del préstamo y cuyo importe se parezca a la
cuota mensual.

Deliberadamente NO actualiza el saldo del préstamo a partir de esto: el saldo
pendiente solo lo da el extracto del prestamista (PDF), un cargo bancario no
lo incluye. Sirve solo para confirmar "sí, se pagó" y ofrecer avanzar la
fecha del próximo pago.
"""

import re
from datetime import date, datetime, timedelta, timezone

from sqlalchemy.orm import Session

from . import models

STOPWORDS = {"DE", "DEL", "LA", "EL", "LOS", "LAS", "Y", "CREDITO", "DIRECTO", "PRESTAMO"}
SEARCH_WINDOW = timedelta(days=40)
AMOUNT_TOLERANCE_RATIO = 0.05
AMOUNT_TOLERANCE_MIN = 2.0


def _keywords(name: str) -> list[str]:
    words = re.findall(r"[A-ZÁÉÍÓÚÑ]{4,}", name.upper())
    return [w for w in words if w not in STOPWORDS]


def find_matching_payment(db: Session, user_id: str, loan: models.Loan) -> models.Transaction | None:
    keywords = _keywords(loan.name)
    if not keywords:
        return None

    today = date.today()
    window_start = loan.next_payment_date.date() - timedelta(days=10) if loan.next_payment_date else today - SEARCH_WINDOW
    date_from = datetime.combine(window_start, datetime.min.time(), tzinfo=timezone.utc)

    tolerance = max(AMOUNT_TOLERANCE_MIN, float(loan.monthly_payment) * AMOUNT_TOLERANCE_RATIO)
    low = float(loan.monthly_payment) - tolerance
    high = float(loan.monthly_payment) + tolerance

    candidates = (
        db.query(models.Transaction)
        .join(models.LinkedAccount)
        .filter(models.LinkedAccount.user_id == user_id)
        .filter(models.Transaction.credit_debit_indicator == "DBIT")
        .filter(models.Transaction.booking_date >= date_from)
        .order_by(models.Transaction.booking_date.desc())
        .all()
    )

    for tx in candidates:
        amount = abs(float(tx.amount))
        if not (low <= amount <= high):
            continue
        haystack = f"{tx.remittance_information or ''} {tx.counterparty_name or ''}".upper()
        if any(keyword in haystack for keyword in keywords):
            return tx
    return None
