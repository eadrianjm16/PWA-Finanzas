"""Script de demo, NO para produccion.

Dos usos:
  python seed_demo.py --write-env   -> genera backend/.env con credenciales
                                        de prueba (clave RSA de usar-y-tirar,
                                        password "demo1234").
  python seed_demo.py               -> siembra cuentas/movimientos/
                                        presupuestos de ejemplo (solo si la
                                        base esta vacia, idempotente).
"""

import argparse
import secrets
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

DEMO_PASSWORD = "demo1234"


def write_env() -> None:
    import bcrypt
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import rsa

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = (
        key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
        .decode()
        .strip()
        .replace("\n", "\\n")
    )

    jwt_secret = secrets.token_urlsafe(32)
    password_hash = bcrypt.hashpw(DEMO_PASSWORD.encode(), bcrypt.gensalt()).decode()

    env_content = (
        "DATABASE_URL=sqlite:///./finanzas.db\n"
        "EB_APPLICATION_ID=demo-application-id\n"
        f'EB_PRIVATE_KEY_PEM="{pem}"\n'
        f"APP_JWT_SECRET={jwt_secret}\n"
        f"APP_PASSWORD_HASH={password_hash}\n"
        "FRONTEND_ORIGIN=http://localhost:3000\n"
        "BACKEND_PUBLIC_URL=http://localhost:8000\n"
    )
    Path(".env").write_text(env_content, encoding="utf-8")
    print(f'backend/.env de demo generado. Contrasena: "{DEMO_PASSWORD}"')
    print("EB_APPLICATION_ID/EB_PRIVATE_KEY_PEM son de prueba: conectar un banco real no funcionara")
    print("hasta que pongas tus credenciales reales de Enable Banking en backend/.env.")


def seed_data() -> None:
    sys.path.insert(0, str(Path(__file__).parent))
    from app import models
    from app.database import SessionLocal, engine
    from app.default_categories import seed_if_needed

    models.Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    seed_if_needed(db)

    if db.query(models.BankConnection).count() > 0:
        print("Ya hay datos de ejemplo en la base, no se vuelve a sembrar.")
        db.close()
        return

    connection = models.BankConnection(aspsp_name="Banco Demo", aspsp_country="ES", key="Banco Demo|ES")
    db.add(connection)
    db.flush()

    account = models.LinkedAccount(
        account_uid="demo-acc-1",
        display_name="Cuenta Corriente",
        iban="ES7620770024003102575766",
        connection_id=connection.id,
        last_balance_amount="1523.40",
        last_balance_currency="EUR",
        last_balance_refreshed_at=datetime.now(timezone.utc),
    )
    db.add(account)
    db.flush()

    # segundo banco/cuenta: sirve para demostrar la deteccion de traspasos
    # internos ("no computable" en Analisis).
    connection2 = models.BankConnection(aspsp_name="Banco Ahorro Demo", aspsp_country="ES", key="Banco Ahorro Demo|ES")
    db.add(connection2)
    db.flush()

    account2 = models.LinkedAccount(
        account_uid="demo-acc-2",
        display_name="Cuenta Ahorro",
        iban="ES1000492352082414205416",
        connection_id=connection2.id,
        last_balance_amount="4200.00",
        last_balance_currency="EUR",
        last_balance_refreshed_at=datetime.now(timezone.utc),
    )
    db.add(account2)
    db.flush()

    categories = {c.name: c for c in db.query(models.Category).all()}
    now = datetime.now(timezone.utc)

    # (categoria, CRDT/DBIT, importe, texto, contraparte, dias atras)
    demo_transactions = [
        ("Nómina/Ingresos", "CRDT", 2100.00, "NOMINA EMPRESA DEMO SL", "Empresa Demo SL", 0),
        ("Alimentación", "DBIT", 25.00, "MERCADONA MADRID", "Mercadona", 1),
        ("Alimentación", "DBIT", 25.00, "MERCADONA MADRID", "Mercadona", 2),  # cargo duplicado a propósito
        ("Alimentación", "DBIT", 38.10, "CARREFOUR EXPRESS", "Carrefour", 3),
        ("Restaurantes", "DBIT", 24.50, "RESTAURANTE LA TASCA", "La Tasca", 4),
        ("Transporte", "DBIT", 45.00, "REPSOL GASOLINERA", "Repsol", 5),
        ("Suscripciones", "DBIT", 12.99, "NETFLIX.COM", "Netflix", 6),
        ("Suscripciones", "DBIT", 9.99, "SPOTIFY", "Spotify", 6),
        ("Suministros", "DBIT", 58.20, "IBERDROLA", "Iberdrola", 7),
        ("Comisiones bancarias", "DBIT", 4.00, "COMISION MANTENIMIENTO CUENTA", None, 2),
        ("Ocio", "DBIT", 35.00, "CINESA", "Cinesa", 9),
        ("Compras", "DBIT", 89.90, "AMAZON.ES", "Amazon", 8),
        ("Alimentación", "DBIT", 71.45, "MERCADONA MADRID", "Mercadona", 8),
        # meses anteriores, solo para poblar el grafico de 6 meses
        ("Nómina/Ingresos", "CRDT", 2050.00, "NOMINA EMPRESA DEMO SL", "Empresa Demo SL", 35),
        ("Alimentación", "DBIT", 140.00, "MERCADONA MADRID", "Mercadona", 33),
        ("Ocio", "DBIT", 60.00, "CINESA", "Cinesa", 30),
        ("Nómina/Ingresos", "CRDT", 2050.00, "NOMINA EMPRESA DEMO SL", "Empresa Demo SL", 65),
        ("Transporte", "DBIT", 90.00, "REPSOL GASOLINERA", "Repsol", 60),
        ("Nómina/Ingresos", "CRDT", 2000.00, "NOMINA EMPRESA DEMO SL", "Empresa Demo SL", 95),
        ("Suministros", "DBIT", 55.00, "IBERDROLA", "Iberdrola", 92),
    ]

    for index, (category_name, indicator, amount, remittance, counterparty, days_ago) in enumerate(demo_transactions):
        category = categories.get(category_name)
        db.add(
            models.Transaction(
                entry_reference=f"demo-tx-{index}",
                account_uid=account.account_uid,
                category_id=category.id if category else None,
                amount=amount,
                currency="EUR",
                credit_debit_indicator=indicator,
                booking_date=now - timedelta(days=days_ago),
                remittance_information=remittance,
                counterparty_name=counterparty,
            )
        )

    # traspaso entre las dos cuentas demo: mismo importe, misma fecha, cuentas
    # distintas -> el detector de traspasos internos debe marcarlas como
    # "no computable" y excluirlas de ingresos/gastos en Analisis.
    db.add(
        models.Transaction(
            entry_reference="demo-tx-transfer-out",
            account_uid=account.account_uid,
            category_id=None,
            amount=200.00,
            currency="EUR",
            credit_debit_indicator="DBIT",
            booking_date=now - timedelta(days=4),
            remittance_information="TRASPASO A CUENTA AHORRO",
        )
    )
    db.add(
        models.Transaction(
            entry_reference="demo-tx-transfer-in",
            account_uid=account2.account_uid,
            category_id=None,
            amount=200.00,
            currency="EUR",
            credit_debit_indicator="CRDT",
            booking_date=now - timedelta(days=4),
            remittance_information="TRASPASO DESDE CUENTA CORRIENTE",
        )
    )

    db.add(models.Budget(category_id=categories["Alimentación"].id, monthly_limit=150))
    db.add(models.Budget(category_id=categories["Ocio"].id, monthly_limit=40))
    db.add(models.Budget(category_id=categories["Suscripciones"].id, monthly_limit=30))

    # deudores de ejemplo
    ana = models.Debtor(name="Ana")
    carlos = models.Debtor(name="Carlos")
    db.add(ana)
    db.add(carlos)
    db.flush()

    db.add(models.DebtEntry(debtor_id=ana.id, amount=40.0, note="Entradas de cine", date=now - timedelta(days=6)))
    db.add(models.DebtEntry(debtor_id=ana.id, amount=-15.0, note="Pago recibido", date=now - timedelta(days=2)))
    # reparto de la cena en La Tasca (demo-tx-4) con Carlos
    db.add(
        models.DebtEntry(
            debtor_id=carlos.id,
            amount=12.25,
            note="La Tasca",
            date=now - timedelta(days=4),
            transaction_entry_reference="demo-tx-4",
        )
    )

    db.commit()
    db.close()
    print("Datos de ejemplo creados: 2 bancos, 2 cuentas, 22 movimientos, 3 presupuestos, 2 deudores.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-env", action="store_true")
    args = parser.parse_args()
    if args.write_env:
        write_env()
    else:
        seed_data()
