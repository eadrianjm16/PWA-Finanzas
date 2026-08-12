"""Detecta gastos recurrentes (suscripciones, cuotas) a partir del historial
de movimientos: agrupa por comercio+importe y comprueba si se repiten con una
cadencia mensual o anual razonablemente constante. Sirve tanto para la
pantalla de Suscripciones como para la previsión de próximos cargos - ambas
son la misma lista, filtrada por fecha en el llamador."""

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session, joinedload

from . import models

LOOKBACK = timedelta(days=400)
MIN_OCCURRENCES = 2

MONTHLY_RANGE = (24, 37)
YEARLY_RANGE = (340, 390)


def _normalized_key(text: str) -> str:
    upper = text.upper()
    return "".join(ch for ch in upper if ch.isalpha() or ch == " ")[:24].strip()


def _frequency_for_gap(days: float) -> str | None:
    if MONTHLY_RANGE[0] <= days <= MONTHLY_RANGE[1]:
        return "mensual"
    if YEARLY_RANGE[0] <= days <= YEARLY_RANGE[1]:
        return "anual"
    return None


def _recurring_candidates(db: Session, user_id: str, indicator: str) -> list[models.Transaction]:
    since = datetime.now(timezone.utc) - LOOKBACK
    return (
        db.query(models.Transaction)
        .join(models.LinkedAccount)
        .filter(models.LinkedAccount.user_id == user_id)
        .filter(models.LinkedAccount.is_visible.is_(True))
        .filter(models.Transaction.credit_debit_indicator == indicator)
        .filter(models.Transaction.booking_date >= since)
        .options(joinedload(models.Transaction.category))
        .order_by(models.Transaction.booking_date)
        .all()
    )


def _detect_recurring(db: Session, user_id: str, indicator: str) -> list[dict]:
    transactions = _recurring_candidates(db, user_id, indicator)

    groups: dict[tuple[str, str, str], list[models.Transaction]] = {}
    for tx in transactions:
        display_name = (tx.counterparty_name or tx.remittance_information or "").split("\n")[0].strip()
        if not display_name:
            continue
        key = (_normalized_key(display_name), f"{float(tx.amount):.2f}", tx.currency)
        groups.setdefault(key, []).append(tx)

    results = []
    for (_, amount_key, currency), group in groups.items():
        if len(group) < MIN_OCCURRENCES:
            continue
        group.sort(key=lambda t: t.booking_date)
        gaps = [
            (group[i].booking_date - group[i - 1].booking_date).days
            for i in range(1, len(group))
        ]

        frequencies = {_frequency_for_gap(gap) for gap in gaps}
        if len(frequencies) != 1 or None in frequencies:
            continue
        frequency = frequencies.pop()

        last = group[-1]
        avg_gap = sum(gaps) / len(gaps)
        next_expected = last.booking_date + timedelta(days=round(avg_gap))
        display_name = (last.counterparty_name or last.remittance_information or "").split("\n")[0].strip()

        prefix = "sub" if indicator == "DBIT" else "inc"
        results.append(
            {
                "id": f"{prefix}-{last.account_uid}-{_normalized_key(display_name)}-{amount_key}",
                "name": display_name,
                "amount": float(amount_key),
                "currency": currency,
                "frequency": frequency,
                "occurrences": len(group),
                "last_charge_date": last.booking_date,
                "next_expected_date": next_expected,
                "category_name": last.category.name if last.category else None,
            }
        )

    results.sort(key=lambda r: r["next_expected_date"])
    return results


def detect_recurring_charges(db: Session, user_id: str) -> list[dict]:
    return _detect_recurring(db, user_id, "DBIT")


def detect_recurring_income(db: Session, user_id: str) -> dict | None:
    """Mejor estimacion de la nomina mensual: entre los ingresos recurrentes
    mensuales detectados, prioriza el categorizado como 'Nómina/Ingresos' (ver
    categorization.py); si no hay ninguno asi, se queda con el de mayor
    importe (mas probable que sea el sueldo que una devolucion recurrente
    pequeña)."""
    incomes = [r for r in _detect_recurring(db, user_id, "CRDT") if r["frequency"] == "mensual"]
    if not incomes:
        return None

    payroll = [r for r in incomes if r["category_name"] == "Nómina/Ingresos"]
    candidates = payroll or incomes
    return max(candidates, key=lambda r: r["amount"])
