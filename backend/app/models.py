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
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
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
    logo: Mapped[str | None] = mapped_column(String, nullable=True)
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
    color: Mapped[str] = mapped_column(String, nullable=False, default="#6366F1")

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

    @property
    def account_color(self) -> str:
        return self.account.color


class AlertDismissal(Base):
    """Marca que un usuario ya vio y descartó una alerta concreta. Las alertas
    no se guardan (se recalculan al vuelo, ver alerts.py); esto solo recuerda
    cuales de esos ids ya se descartaron para no volver a mostrarlas."""

    __tablename__ = "alert_dismissals"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), primary_key=True)
    alert_id: Mapped[str] = mapped_column(String, primary_key=True)
    dismissed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class PushSubscription(Base):
    """Suscripcion Web Push del navegador de un usuario (puede tener varias:
    movil, escritorio, etc)."""

    __tablename__ = "push_subscriptions"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_gen_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    endpoint: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    p256dh: Mapped[str] = mapped_column(String, nullable=False)
    auth: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class NotifiedAlert(Base):
    """Que alertas ya dispararon un push a un usuario, para no reenviar la
    misma notificacion en cada sync mientras la alerta siga activa."""

    __tablename__ = "notified_alerts"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), primary_key=True)
    alert_id: Mapped[str] = mapped_column(String, primary_key=True)
    notified_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class NetWorthSnapshot(Base):
    """Una foto del saldo total del usuario en un dia concreto. Sin cron en el
    plan gratuito de Render, se toma (upsert) cada vez que el usuario abre la
    pantalla Saldo (ver GET /api/banks/connections) en vez de en un job
    periodico - basta para ver una tendencia con uso normal de la app."""

    __tablename__ = "net_worth_snapshots"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), primary_key=True)
    date: Mapped[str] = mapped_column(String, primary_key=True)  # "YYYY-MM-DD"
    total_amount: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False)


class Budget(Base):
    """Limite mensual por categoria. A diferencia del modelo iOS (que unia por
    categoryName), aqui se referencia la categoria por FK: mismo dato, join
    mas simple. El scope por usuario viene transitivamente de category.user_id."""

    __tablename__ = "budgets"

    category_id: Mapped[str] = mapped_column(ForeignKey("categories.id"), primary_key=True)
    monthly_limit: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False)
    rollover: Mapped[bool] = mapped_column(Boolean, default=False)

    category: Mapped["Category"] = relationship()


class CategorizationRule(Base):
    """Regla propia del usuario: si el comercio/concepto de un movimiento
    contiene `keyword`, se le asigna `category_id` en vez de (o antes que) la
    sugerencia automatica de categorizacion.py."""

    __tablename__ = "categorization_rules"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_gen_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    keyword: Mapped[str] = mapped_column(String, nullable=False)
    category_id: Mapped[str] = mapped_column(ForeignKey("categories.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    category: Mapped["Category"] = relationship()


class SavingsGoal(Base):
    """Meta de ahorro. Por defecto es manual (el usuario actualiza
    current_amount el mismo). Si se vincula a una cuenta real
    (linked_account_uid), el progreso pasa a ser el saldo de esa cuenta -
    pensado para una cuenta de ahorro dedicada, donde el saldo entero
    representa el progreso, no un delta desde que se vinculo."""

    __tablename__ = "savings_goals"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_gen_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    target_amount: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False)
    current_amount: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    linked_account_uid: Mapped[str | None] = mapped_column(ForeignKey("linked_accounts.account_uid"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    linked_account: Mapped["LinkedAccount | None"] = relationship()


class WeeklyDigestLog(Base):
    """Que semana (ISO, p.ej. '2026-W33') ya recibio su resumen push, para no
    repetirlo cada vez que el usuario sincroniza en la misma semana."""

    __tablename__ = "weekly_digest_log"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), primary_key=True)
    week_key: Mapped[str] = mapped_column(String, primary_key=True)
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class FixedExpense(Base):
    """Gasto fijo mensual gestionado a mano (alquiler, seguro...), tipo TODO:
    no se deriva de movimientos bancarios, el usuario la marca como pagada
    cada mes (ver FixedExpenseCheck)."""

    __tablename__ = "fixed_expenses"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_gen_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False)
    due_day: Mapped[int] = mapped_column(Integer, nullable=False)  # dia del mes, 1-31
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class FixedExpenseCheck(Base):
    """Que gasto fijo se marco como pagado en que mes ('YYYY-MM'). La fila
    solo existe si esta marcado - el mes siguiente no hay fila y vuelve a
    aparecer sin marcar, sin necesidad de resetear nada de forma activa."""

    __tablename__ = "fixed_expense_checks"

    fixed_expense_id: Mapped[str] = mapped_column(ForeignKey("fixed_expenses.id"), primary_key=True)
    month_key: Mapped[str] = mapped_column(String, primary_key=True)
    checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class IncomeOverride(Base):
    """Nomina mensual escrita a mano por el usuario, que manda sobre la
    detectada automaticamente en recurring.py si esta presente."""

    __tablename__ = "income_overrides"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), primary_key=True)
    monthly_amount: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False)


class Debtor(Base):
    """Una persona a la que se le ha prestado dinero o se le debe (deudas
    manuales o repartos de un movimiento)."""

    __tablename__ = "debtors"
    __table_args__ = (UniqueConstraint("user_id", "name", name="uq_debtors_user_name"),)

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_gen_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    phone: Mapped[str | None] = mapped_column(String, nullable=True)
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


class Loan(Base):
    """Seguimiento manual de un préstamo o crédito revolving externo (p. ej.
    Cofidis, Cetelem) que no llega por sincronización bancaria: el usuario
    actualiza estos campos a mano cada vez que recibe un extracto nuevo."""

    __tablename__ = "loans"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_gen_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    credit_limit: Mapped[float | None] = mapped_column(Numeric(18, 2), nullable=True)
    balance: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False)
    monthly_payment: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False)
    tin: Mapped[float | None] = mapped_column(Numeric(6, 2), nullable=True)
    tae: Mapped[float | None] = mapped_column(Numeric(6, 2), nullable=True)
    next_payment_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)
