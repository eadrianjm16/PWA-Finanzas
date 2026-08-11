import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def _gen_id() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_gen_id)
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class BankConnection(Base):
    """Una entidad bancaria (p. ej. 'Banco Santander'), con N LinkedAccount."""

    __tablename__ = "bank_connections"
    __table_args__ = (UniqueConstraint("user_id", "key", name="uq_bank_connections_user_key"),)

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_gen_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    key: Mapped[str] = mapped_column(String, nullable=False)
    aspsp_name: Mapped[str] = mapped_column(String, nullable=False)
    aspsp_country: Mapped[str] = mapped_column(String, nullable=False)
    linked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    accounts: Mapped[list["LinkedAccount"]] = relationship(
        back_populates="connection", cascade="all, delete-orphan"
    )


class LinkedAccount(Base):
    """Una cuenta/producto individual dentro de un BankConnection."""

    __tablename__ = "linked_accounts"

    account_uid: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    connection_id: Mapped[str] = mapped_column(ForeignKey("bank_connections.id"), nullable=False)
    display_name: Mapped[str] = mapped_column(String, nullable=False)
    iban: Mapped[str | None] = mapped_column(String, nullable=True)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_balance_amount: Mapped[str | None] = mapped_column(String, nullable=True)
    last_balance_currency: Mapped[str | None] = mapped_column(String, nullable=True)
    last_balance_refreshed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    linked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    is_visible: Mapped[bool] = mapped_column(Boolean, default=True)
    is_balance_visible: Mapped[bool] = mapped_column(Boolean, default=True)
    last_sync_issue: Mapped[str | None] = mapped_column(String, nullable=True)

    connection: Mapped["BankConnection"] = relationship(back_populates="accounts")
    transactions: Mapped[list["Transaction"]] = relationship(
        back_populates="account", cascade="all, delete-orphan"
    )


class Category(Base):
    __tablename__ = "categories"
    __table_args__ = (UniqueConstraint("user_id", "name", name="uq_categories_user_name"),)

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_gen_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    system_icon_name: Mapped[str] = mapped_column(String, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    transactions: Mapped[list["Transaction"]] = relationship(back_populates="category")


class Transaction(Base):
    __tablename__ = "transactions"

    entry_reference: Mapped[str] = mapped_column(String, primary_key=True)
    account_uid: Mapped[str] = mapped_column(ForeignKey("linked_accounts.account_uid"), nullable=False)
    category_id: Mapped[str | None] = mapped_column(ForeignKey("categories.id"), nullable=True)
    amount: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String, nullable=False)
    credit_debit_indicator: Mapped[str] = mapped_column(String, nullable=False)
    booking_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    value_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    remittance_information: Mapped[str] = mapped_column(String, default="")
    counterparty_name: Mapped[str | None] = mapped_column(String, nullable=True)
    merchant_category_code: Mapped[str | None] = mapped_column(String, nullable=True)
    status: Mapped[str | None] = mapped_column(String, nullable=True)
    is_user_categorized: Mapped[bool] = mapped_column(Boolean, default=False)

    account: Mapped["LinkedAccount"] = relationship(back_populates="transactions")
    category: Mapped["Category | None"] = relationship(back_populates="transactions")
    debt_entries: Mapped[list["DebtEntry"]] = relationship(back_populates="transaction")

    @property
    def has_debt_entries(self) -> bool:
        return len(self.debt_entries) > 0


class Budget(Base):
    """Limite mensual por categoria. A diferencia del modelo iOS (que unia por
    categoryName), aqui se referencia la categoria por FK: mismo dato, join
    mas simple. El scope por usuario viene transitivamente de category.user_id."""

    __tablename__ = "budgets"

    category_id: Mapped[str] = mapped_column(ForeignKey("categories.id"), primary_key=True)
    monthly_limit: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False)

    category: Mapped["Category"] = relationship()


class Debtor(Base):
    """Una persona a la que se le ha prestado dinero o se le debe (deudas
    manuales o repartos de un movimiento)."""

    __tablename__ = "debtors"
    __table_args__ = (UniqueConstraint("user_id", "name", name="uq_debtors_user_name"),)

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_gen_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    entries: Mapped[list["DebtEntry"]] = relationship(back_populates="debtor", cascade="all, delete-orphan")


class DebtEntry(Base):
    """amount positivo = te deben; negativo = le debes / pago recibido."""

    __tablename__ = "debt_entries"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_gen_id)
    debtor_id: Mapped[str] = mapped_column(ForeignKey("debtors.id"), nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False)
    date: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    note: Mapped[str | None] = mapped_column(String, nullable=True)
    transaction_entry_reference: Mapped[str | None] = mapped_column(
        ForeignKey("transactions.entry_reference"), nullable=True
    )

    debtor: Mapped["Debtor"] = relationship(back_populates="entries")
    transaction: Mapped["Transaction | None"] = relationship(back_populates="debt_entries")
