from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from .. import models, schemas
from ..deps import CurrentUser, get_current_user, get_db_session

router = APIRouter(prefix="/api/categorization-rules", tags=["categorization-rules"])


@router.get("", response_model=list[schemas.CategorizationRuleOut])
def list_rules(
    db: Session = Depends(get_db_session), user: CurrentUser = Depends(get_current_user)
) -> list[models.CategorizationRule]:
    return (
        db.query(models.CategorizationRule)
        .filter_by(user_id=user.id)
        .options(joinedload(models.CategorizationRule.category))
        .order_by(models.CategorizationRule.created_at)
        .all()
    )


@router.post("", response_model=schemas.CategorizationRuleOut, status_code=status.HTTP_201_CREATED)
def create_rule(
    payload: schemas.CategorizationRuleCreateRequest,
    db: Session = Depends(get_db_session),
    user: CurrentUser = Depends(get_current_user),
) -> models.CategorizationRule:
    keyword = payload.keyword.strip()
    if not keyword:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "La palabra clave no puede estar vacía")
    category = db.query(models.Category).filter_by(id=payload.category_id, user_id=user.id).first()
    if category is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Categoría no encontrada")

    rule = models.CategorizationRule(user_id=user.id, keyword=keyword, category_id=category.id)
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule


@router.delete("/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_rule(
    rule_id: str, db: Session = Depends(get_db_session), user: CurrentUser = Depends(get_current_user)
) -> None:
    rule = db.query(models.CategorizationRule).filter_by(id=rule_id, user_id=user.id).first()
    if rule is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Regla no encontrada")
    db.delete(rule)
    db.commit()
