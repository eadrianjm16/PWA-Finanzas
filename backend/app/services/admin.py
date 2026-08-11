"""Borrado completo de un usuario y todos sus datos. Se hace con deletes
explicitos en orden (hijos antes que padres) en vez de confiar en cascadas
del ORM: es una operacion destructiva e irreversible, preferimos que quede
claro exactamente que se borra y en que orden."""

from sqlalchemy.orm import Session

from .. import models


def delete_user_completely(db: Session, user_id: str) -> None:
    debtor_ids = [row[0] for row in db.query(models.Debtor.id).filter_by(user_id=user_id).all()]
    if debtor_ids:
        db.query(models.DebtEntry).filter(models.DebtEntry.debtor_id.in_(debtor_ids)).delete(
            synchronize_session=False
        )
    db.query(models.Debtor).filter_by(user_id=user_id).delete(synchronize_session=False)

    category_ids = [row[0] for row in db.query(models.Category.id).filter_by(user_id=user_id).all()]
    if category_ids:
        db.query(models.Budget).filter(models.Budget.category_id.in_(category_ids)).delete(
            synchronize_session=False
        )

    account_uids = [
        row[0] for row in db.query(models.LinkedAccount.account_uid).filter_by(user_id=user_id).all()
    ]
    if account_uids:
        db.query(models.Transaction).filter(models.Transaction.account_uid.in_(account_uids)).delete(
            synchronize_session=False
        )

    db.query(models.LinkedAccount).filter_by(user_id=user_id).delete(synchronize_session=False)
    db.query(models.BankConnection).filter_by(user_id=user_id).delete(synchronize_session=False)
    db.query(models.Category).filter_by(user_id=user_id).delete(synchronize_session=False)
    db.query(models.User).filter_by(id=user_id).delete(synchronize_session=False)
    db.commit()
