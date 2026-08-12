from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, selectinload

from .. import models, schemas
from ..deps import CurrentUser, get_current_user, get_db_session

router = APIRouter(prefix="/api/debtors", tags=["debtors"])


def _balance(debtor: models.Debtor) -> float:
    return sum(float(entry.amount) for entry in debtor.entries)


def _normalize_phone(raw: str | None) -> str | None:
    """Da igual cómo se escriba el teléfono (a mano, pegado de contactos...):
    si no trae ya un prefijo de país explícito (+34, +51...), se asume
    España. Así el enlace de WhatsApp (wa.me, que exige el prefijo) siempre
    funciona sin que el usuario tenga que acordarse de escribirlo."""
    trimmed = (raw or "").strip()
    if not trimmed:
        return None
    if trimmed.startswith("+"):
        return trimmed
    return f"+34 {trimmed}"


def _to_out(debtor: models.Debtor) -> schemas.DebtorOut:
    return schemas.DebtorOut(
        id=debtor.id, name=debtor.name, phone=debtor.phone, created_at=debtor.created_at, balance=_balance(debtor)
    )


def _get_debtor_or_404(db: Session, user: CurrentUser, debtor_id: str) -> models.Debtor:
    debtor = db.query(models.Debtor).filter_by(id=debtor_id, user_id=user.id).first()
    if debtor is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Deudor no encontrado")
    return debtor


@router.get("", response_model=list[schemas.DebtorOut])
def list_debtors(
    db: Session = Depends(get_db_session), user: CurrentUser = Depends(get_current_user)
) -> list[schemas.DebtorOut]:
    debtors = (
        db.query(models.Debtor)
        .filter_by(user_id=user.id)
        .options(selectinload(models.Debtor.entries))
        .order_by(models.Debtor.name)
        .all()
    )
    return [_to_out(d) for d in debtors]


@router.post("", response_model=schemas.DebtorOut, status_code=status.HTTP_201_CREATED)
def create_debtor(
    payload: schemas.DebtorCreateRequest,
    db: Session = Depends(get_db_session),
    user: CurrentUser = Depends(get_current_user),
) -> schemas.DebtorOut:
    name = payload.name.strip()
    if not name:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "El nombre no puede estar vacío")
    if db.query(models.Debtor).filter_by(user_id=user.id, name=name).first() is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Ya existe una persona con ese nombre")

    debtor = models.Debtor(user_id=user.id, name=name, phone=_normalize_phone(payload.phone))
    db.add(debtor)
    db.commit()
    db.refresh(debtor)
    return _to_out(debtor)


@router.patch("/{debtor_id}", response_model=schemas.DebtorOut)
def update_debtor(
    debtor_id: str,
    payload: schemas.DebtorUpdateRequest,
    db: Session = Depends(get_db_session),
    user: CurrentUser = Depends(get_current_user),
) -> schemas.DebtorOut:
    debtor = _get_debtor_or_404(db, user, debtor_id)
    updates = payload.model_dump(exclude_unset=True)

    if "name" in updates:
        name = (updates["name"] or "").strip()
        if not name:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "El nombre no puede estar vacío")
        debtor.name = name
    if "phone" in updates:
        debtor.phone = _normalize_phone(updates["phone"])

    db.commit()
    db.refresh(debtor)
    return _to_out(debtor)


@router.get("/{debtor_id}", response_model=schemas.DebtorDetailOut)
def get_debtor(
    debtor_id: str, db: Session = Depends(get_db_session), user: CurrentUser = Depends(get_current_user)
) -> schemas.DebtorDetailOut:
    debtor = _get_debtor_or_404(db, user, debtor_id)
    entries = sorted(debtor.entries, key=lambda e: e.date, reverse=True)
    return schemas.DebtorDetailOut(
        id=debtor.id,
        name=debtor.name,
        phone=debtor.phone,
        created_at=debtor.created_at,
        balance=_balance(debtor),
        entries=[schemas.DebtEntryOut.model_validate(e) for e in entries],
    )


@router.delete("/{debtor_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_debtor(
    debtor_id: str, db: Session = Depends(get_db_session), user: CurrentUser = Depends(get_current_user)
) -> None:
    debtor = _get_debtor_or_404(db, user, debtor_id)
    db.delete(debtor)
    db.commit()


@router.post("/{debtor_id}/entries", response_model=schemas.DebtorDetailOut)
def add_entry(
    debtor_id: str,
    payload: schemas.DebtEntryCreateRequest,
    db: Session = Depends(get_db_session),
    user: CurrentUser = Depends(get_current_user),
) -> schemas.DebtorDetailOut:
    debtor = _get_debtor_or_404(db, user, debtor_id)
    if payload.amount == 0:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "El importe no puede ser 0")
    db.add(models.DebtEntry(debtor_id=debtor.id, amount=payload.amount, note=payload.note))
    db.commit()
    db.refresh(debtor)
    return get_debtor(debtor_id, db, user)


@router.post("/{debtor_id}/payments", response_model=schemas.DebtorDetailOut)
def register_payment(
    debtor_id: str,
    payload: schemas.DebtPaymentRequest,
    db: Session = Depends(get_db_session),
    user: CurrentUser = Depends(get_current_user),
) -> schemas.DebtorDetailOut:
    debtor = _get_debtor_or_404(db, user, debtor_id)
    if payload.amount <= 0:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "El importe debe ser mayor que 0")

    is_owed_to_me = _balance(debtor) >= 0
    db.add(
        models.DebtEntry(
            debtor_id=debtor.id,
            amount=-payload.amount if is_owed_to_me else payload.amount,
            note="Pago recibido" if is_owed_to_me else "Pago realizado",
        )
    )
    db.commit()
    return get_debtor(debtor_id, db, user)


@router.post("/{debtor_id}/cancel", response_model=schemas.DebtorDetailOut)
def cancel_debt(
    debtor_id: str, db: Session = Depends(get_db_session), user: CurrentUser = Depends(get_current_user)
) -> schemas.DebtorDetailOut:
    debtor = _get_debtor_or_404(db, user, debtor_id)
    balance = _balance(debtor)
    if balance == 0:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "No hay deuda pendiente")
    db.add(models.DebtEntry(debtor_id=debtor.id, amount=-balance, note="Deuda cancelada"))
    db.commit()
    return get_debtor(debtor_id, db, user)


@router.delete("/{debtor_id}/entries/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_entry(
    debtor_id: str,
    entry_id: str,
    db: Session = Depends(get_db_session),
    user: CurrentUser = Depends(get_current_user),
) -> None:
    _get_debtor_or_404(db, user, debtor_id)
    entry = db.get(models.DebtEntry, entry_id)
    if entry is None or entry.debtor_id != debtor_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Movimiento de deuda no encontrado")
    db.delete(entry)
    db.commit()
