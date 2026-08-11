from sqlalchemy.orm import Session

from . import models

OTROS_NAME = "Otros"

SEED: list[tuple[str, str]] = [
    ("Nómina/Ingresos", "arrow-down-circle"),
    ("Alimentación", "shopping-cart"),
    ("Restaurantes", "utensils"),
    ("Transporte", "car"),
    ("Vivienda/Hogar", "home"),
    ("Suministros", "zap"),
    ("Salud", "cross"),
    ("Ocio", "gamepad-2"),
    ("Compras", "shopping-bag"),
    ("Suscripciones", "repeat"),
    ("Comisiones bancarias", "landmark"),
    (OTROS_NAME, "help-circle"),
]


def seed_categories_for_user(db: Session, user_id: str) -> None:
    existing = db.query(models.Category).filter_by(user_id=user_id).count()
    if existing > 0:
        return
    for index, (name, icon) in enumerate(SEED):
        db.add(models.Category(user_id=user_id, name=name, system_icon_name=icon, sort_order=index))
    db.commit()
