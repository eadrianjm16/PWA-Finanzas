from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from .. import models, schemas
from ..deps import CurrentUser, get_current_user, get_db_session

router = APIRouter(prefix="/api/savings-goals", tags=["savings-goals"])


def _get_goal_or_404(db: Session, user: CurrentUser, goal_id: str) -> models.SavingsGoal:
    goal = (
        db.query(models.SavingsGoal)
        .filter_by(id=goal_id, user_id=user.id)
        .options(joinedload(models.SavingsGoal.linked_account))
        .first()
    )
    if goal is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Meta no encontrada")
    return goal


def _to_out(goal: models.SavingsGoal) -> schemas.SavingsGoalOut:
    # Vinculada a una cuenta real: el progreso es el saldo de esa cuenta tal
    # cual (pensado para una cuenta de ahorro dedicada), no lo que haya
    # guardado en current_amount - eso solo se usa para metas manuales.
    if goal.linked_account is not None:
        raw_balance = goal.linked_account.last_balance_amount
        current_amount = float(raw_balance) if raw_balance else 0.0
        linked_account_name = goal.linked_account.display_name
    else:
        current_amount = float(goal.current_amount)
        linked_account_name = None

    return schemas.SavingsGoalOut(
        id=goal.id,
        name=goal.name,
        target_amount=float(goal.target_amount),
        current_amount=current_amount,
        linked_account_uid=goal.linked_account_uid,
        linked_account_name=linked_account_name,
        created_at=goal.created_at,
    )


@router.get("", response_model=list[schemas.SavingsGoalOut])
def list_goals(
    db: Session = Depends(get_db_session), user: CurrentUser = Depends(get_current_user)
) -> list[schemas.SavingsGoalOut]:
    goals = (
        db.query(models.SavingsGoal)
        .filter_by(user_id=user.id)
        .options(joinedload(models.SavingsGoal.linked_account))
        .order_by(models.SavingsGoal.created_at)
        .all()
    )
    return [_to_out(g) for g in goals]


@router.post("", response_model=schemas.SavingsGoalOut, status_code=status.HTTP_201_CREATED)
def create_goal(
    payload: schemas.SavingsGoalCreateRequest,
    db: Session = Depends(get_db_session),
    user: CurrentUser = Depends(get_current_user),
) -> schemas.SavingsGoalOut:
    if payload.target_amount <= 0:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "El objetivo debe ser mayor que 0")

    linked_account_uid = None
    if payload.linked_account_uid is not None:
        account = db.query(models.LinkedAccount).filter_by(
            account_uid=payload.linked_account_uid, user_id=user.id
        ).first()
        if account is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Cuenta no encontrada")
        linked_account_uid = account.account_uid

    goal = models.SavingsGoal(
        user_id=user.id,
        name=payload.name.strip(),
        target_amount=payload.target_amount,
        linked_account_uid=linked_account_uid,
    )
    db.add(goal)
    db.commit()
    db.refresh(goal)
    return _to_out(_get_goal_or_404(db, user, goal.id))


@router.put("/{goal_id}/link", response_model=schemas.SavingsGoalOut)
def link_goal_to_account(
    goal_id: str,
    payload: schemas.SavingsGoalLinkRequest,
    db: Session = Depends(get_db_session),
    user: CurrentUser = Depends(get_current_user),
) -> schemas.SavingsGoalOut:
    goal = _get_goal_or_404(db, user, goal_id)

    if payload.account_uid is None:
        goal.linked_account_uid = None
    else:
        account = db.query(models.LinkedAccount).filter_by(account_uid=payload.account_uid, user_id=user.id).first()
        if account is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Cuenta no encontrada")
        goal.linked_account_uid = account.account_uid
    db.commit()
    return _to_out(_get_goal_or_404(db, user, goal_id))


@router.post("/{goal_id}/contribute", response_model=schemas.SavingsGoalOut)
def contribute_to_goal(
    goal_id: str,
    payload: schemas.SavingsGoalContributeRequest,
    db: Session = Depends(get_db_session),
    user: CurrentUser = Depends(get_current_user),
) -> schemas.SavingsGoalOut:
    goal = _get_goal_or_404(db, user, goal_id)
    if goal.linked_account_uid is not None:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Esta meta está vinculada a una cuenta real: el progreso se actualiza solo con el saldo, no se añade a mano",
        )
    goal.current_amount = max(0, float(goal.current_amount) + payload.amount)
    db.commit()
    return _to_out(_get_goal_or_404(db, user, goal_id))


@router.delete("/{goal_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_goal(
    goal_id: str, db: Session = Depends(get_db_session), user: CurrentUser = Depends(get_current_user)
) -> None:
    goal = _get_goal_or_404(db, user, goal_id)
    db.delete(goal)
    db.commit()
