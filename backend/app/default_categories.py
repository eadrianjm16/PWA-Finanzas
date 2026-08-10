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


def seed_if_needed(db: Session) -> None:
    if db.query(models.Category).count() > 0:
        return
    for index, (name, icon) in enumerate(SEED):
        db.add(models.Category(name=name, system_icon_name=icon, sort_order=index))
    db.commit()
