from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import models, schemas
from ..deps import CurrentUser, get_current_user, get_db_session

router = APIRouter(prefix="/api/savings-goals", tags=["savings-goals"])


def _get_goal_or_404(db: Session, user: CurrentUser, goal_id: str) -> models.SavingsGoal:
    goal = db.query(models.SavingsGoal).filter_by(id=goal_id, user_id=user.id).first()
    if goal is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Meta no encontrada")
    return goal


@router.get("", response_model=list[schemas.SavingsGoalOut])
def list_goals(
    db: Session = Depends(get_db_session), user: CurrentUser = Depends(get_current_user)
) -> list[models.SavingsGoal]:
    return db.query(models.SavingsGoal).filter_by(user_id=user.id).order_by(models.SavingsGoal.created_at).all()


@router.post("", response_model=schemas.SavingsGoalOut, status_code=status.HTTP_201_CREATED)
def create_goal(
    payload: schemas.SavingsGoalCreateRequest,
    db: Session = Depends(get_db_session),
    user: CurrentUser = Depends(get_current_user),
) -> models.SavingsGoal:
    if payload.target_amount <= 0:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "El objetivo debe ser mayor que 0")
    goal = models.SavingsGoal(user_id=user.id, name=payload.name.strip(), target_amount=payload.target_amount)
    db.add(goal)
    db.commit()
    db.refresh(goal)
    return goal


@router.post("/{goal_id}/contribute", response_model=schemas.SavingsGoalOut)
def contribute_to_goal(
    goal_id: str,
    payload: schemas.SavingsGoalContributeRequest,
    db: Session = Depends(get_db_session),
    user: CurrentUser = Depends(get_current_user),
) -> models.SavingsGoal:
    goal = _get_goal_or_404(db, user, goal_id)
    goal.current_amount = max(0, float(goal.current_amount) + payload.amount)
    db.commit()
    db.refresh(goal)
    return goal


@router.delete("/{goal_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_goal(
    goal_id: str, db: Session = Depends(get_db_session), user: CurrentUser = Depends(get_current_user)
) -> None:
    goal = _get_goal_or_404(db, user, goal_id)
    db.delete(goal)
    db.commit()
