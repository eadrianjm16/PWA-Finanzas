from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import models, schemas
from ..default_categories import OTROS_NAME
from ..deps import CurrentUser, get_current_user, get_db_session

router = APIRouter(prefix="/api/categories", tags=["categories"])


def _get_category_or_404(db: Session, user: CurrentUser, category_id: str) -> models.Category:
    category = db.query(models.Category).filter_by(id=category_id, user_id=user.id).first()
    if category is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Categoría no encontrada")
    return category


@router.get("", response_model=list[schemas.CategoryOut])
def list_categories(
    db: Session = Depends(get_db_session), user: CurrentUser = Depends(get_current_user)
) -> list[models.Category]:
    return db.query(models.Category).filter_by(user_id=user.id).order_by(models.Category.sort_order).all()


@router.post("", response_model=schemas.CategoryOut, status_code=status.HTTP_201_CREATED)
def create_category(
    payload: schemas.CategoryCreateRequest,
    db: Session = Depends(get_db_session),
    user: CurrentUser = Depends(get_current_user),
) -> models.Category:
    name = payload.name.strip()
    if not name:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "El nombre no puede estar vacío")
    if db.query(models.Category).filter_by(user_id=user.id, name=name).first() is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Ya existe una categoría con ese nombre")

    max_order = db.query(models.Category).filter_by(user_id=user.id).count()
    category = models.Category(user_id=user.id, name=name, system_icon_name=payload.system_icon_name, sort_order=max_order)
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


@router.patch("/{category_id}", response_model=schemas.CategoryOut)
def update_category(
    category_id: str,
    payload: schemas.CategoryUpdateRequest,
    db: Session = Depends(get_db_session),
    user: CurrentUser = Depends(get_current_user),
) -> models.Category:
    category = _get_category_or_404(db, user, category_id)

    if payload.name is not None:
        name = payload.name.strip()
        if not name:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "El nombre no puede estar vacío")
        if name != category.name and db.query(models.Category).filter_by(user_id=user.id, name=name).first() is not None:
            raise HTTPException(status.HTTP_409_CONFLICT, "Ya existe una categoría con ese nombre")
        category.name = name

    if payload.system_icon_name is not None:
        category.system_icon_name = payload.system_icon_name

    db.commit()
    db.refresh(category)
    return category


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(
    category_id: str, db: Session = Depends(get_db_session), user: CurrentUser = Depends(get_current_user)
) -> None:
    category = _get_category_or_404(db, user, category_id)
    if category.name == OTROS_NAME:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "No se puede borrar la categoría Otros")

    otros = db.query(models.Category).filter_by(user_id=user.id, name=OTROS_NAME).first()
    for transaction in category.transactions:
        transaction.category_id = otros.id if otros else None

    budget = db.get(models.Budget, category_id)
    if budget is not None:
        db.delete(budget)

    db.delete(category)
    db.commit()


@router.put("/reorder", response_model=list[schemas.CategoryOut])
def reorder_categories(
    payload: schemas.CategoryReorderRequest,
    db: Session = Depends(get_db_session),
    user: CurrentUser = Depends(get_current_user),
) -> list[models.Category]:
    categories = {c.id: c for c in db.query(models.Category).filter_by(user_id=user.id).all()}
    missing = [cid for cid in payload.ordered_ids if cid not in categories]
    if missing:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Categorías no encontradas: {', '.join(missing)}")

    for index, category_id in enumerate(payload.ordered_ids):
        categories[category_id].sort_order = index
    db.commit()

    return db.query(models.Category).filter_by(user_id=user.id).order_by(models.Category.sort_order).all()
