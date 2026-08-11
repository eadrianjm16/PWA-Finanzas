from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import models, schemas
from ..deps import CurrentUser, get_current_admin, get_db_session
from ..services.admin import delete_user_completely

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/users", response_model=list[schemas.AdminUserOut])
def list_users(
    db: Session = Depends(get_db_session), admin: CurrentUser = Depends(get_current_admin)
) -> list[schemas.AdminUserOut]:
    users = db.query(models.User).order_by(models.User.created_at).all()
    result = []
    for user in users:
        result.append(
            schemas.AdminUserOut(
                id=user.id,
                email=user.email,
                is_admin=user.is_admin,
                created_at=user.created_at,
                bank_connections_count=db.query(models.BankConnection).filter_by(user_id=user.id).count(),
                transactions_count=(
                    db.query(models.Transaction)
                    .join(models.LinkedAccount)
                    .filter(models.LinkedAccount.user_id == user.id)
                    .count()
                ),
                debtors_count=db.query(models.Debtor).filter_by(user_id=user.id).count(),
            )
        )
    return result


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: str, db: Session = Depends(get_db_session), admin: CurrentUser = Depends(get_current_admin)
) -> None:
    if user_id == admin.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "No puedes borrar tu propia cuenta desde aquí")
    target = db.get(models.User, user_id)
    if target is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Usuario no encontrado")
    delete_user_completely(db, user_id)
