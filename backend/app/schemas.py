from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    invite_code: str | None = None


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class MessageResponse(BaseModel):
    message: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str
    is_admin: bool
    created_at: datetime


class AdminUserOut(BaseModel):
    id: str
    email: str
    is_admin: bool
    created_at: datetime
    bank_connections_count: int
    transactions_count: int
    debtors_count: int


class ASPSPOut(BaseModel):
    name: str
    country: str
    logo: str | None = None
    bic: str | None = None


class StartAuthorizationRequest(BaseModel):
    aspsp: ASPSPOut


class StartAuthorizationResponse(BaseModel):
    url: str


class CategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    system_icon_name: str
    sort_order: int


class LinkedAccountOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    account_uid: str
    display_name: str
    iban: str | None
    last_synced_at: datetime | None
    last_balance_amount: str | None
    last_balance_currency: str | None
    last_balance_refreshed_at: datetime | None
    is_visible: bool
    is_balance_visible: bool
    last_sync_issue: str | None


class BankConnectionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    aspsp_name: str
    aspsp_country: str
    linked_at: datetime
    accounts: list[LinkedAccountOut]


class AccountUpdateRequest(BaseModel):
    display_name: str | None = None
    is_visible: bool | None = None
    is_balance_visible: bool | None = None


class TransactionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    entry_reference: str
    account_uid: str
    category: CategoryOut | None
    amount: float
    currency: str
    credit_debit_indicator: str
    booking_date: datetime
    value_date: datetime | None
    remittance_information: str
    counterparty_name: str | None
    merchant_category_code: str | None
    status: str | None
    is_user_categorized: bool
    has_debt_entries: bool = False


class TransactionCategorizeRequest(BaseModel):
    category_id: str


class SyncResult(BaseModel):
    account_uid: str
    ok: bool
    error: str | None = None


class CategoryCreateRequest(BaseModel):
    name: str
    system_icon_name: str


class CategoryUpdateRequest(BaseModel):
    name: str | None = None
    system_icon_name: str | None = None


class CategoryReorderRequest(BaseModel):
    ordered_ids: list[str]


class RecategorizeResult(BaseModel):
    updated_count: int


class DebtEntryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    amount: float
    date: datetime
    note: str | None
    transaction_entry_reference: str | None


class DebtorOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    created_at: datetime
    balance: float


class DebtorDetailOut(BaseModel):
    id: str
    name: str
    created_at: datetime
    balance: float
    entries: list[DebtEntryOut]


class DebtorCreateRequest(BaseModel):
    name: str


class DebtEntryCreateRequest(BaseModel):
    amount: float  # positivo = deuda a cobrar, negativo = deuda a pagar (le debo)
    note: str | None = None


class DebtPaymentRequest(BaseModel):
    amount: float  # siempre positivo; el signo se decide según a favor de quién esté el saldo


class SplitEntry(BaseModel):
    debtor_id: str
    amount: float


class SplitTransactionRequest(BaseModel):
    entries: list[SplitEntry]


class BudgetOut(BaseModel):
    category: CategoryOut
    monthly_limit: float | None
    effective_limit: float | None  # monthly_limit + remanente del mes anterior si rollover=True
    rollover: bool
    spent_this_month: float


class BudgetUpsertRequest(BaseModel):
    monthly_limit: float
    rollover: bool = False


class AlertOut(BaseModel):
    id: str
    icon: str
    title: str
    subtitle: str


class PushSubscriptionKeys(BaseModel):
    p256dh: str
    auth: str


class PushSubscribeRequest(BaseModel):
    endpoint: str
    keys: PushSubscriptionKeys


class PushUnsubscribeRequest(BaseModel):
    endpoint: str


class VapidPublicKeyOut(BaseModel):
    public_key: str
    enabled: bool


class RecurringChargeOut(BaseModel):
    id: str
    name: str
    amount: float
    currency: str
    frequency: str  # "mensual" | "anual"
    occurrences: int
    last_charge_date: datetime
    next_expected_date: datetime
    category_name: str | None


class NetWorthPointOut(BaseModel):
    date: str  # "YYYY-MM-DD"
    total_amount: float


class CategorizationRuleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    keyword: str
    category: CategoryOut


class CategorizationRuleCreateRequest(BaseModel):
    keyword: str
    category_id: str


class SavingsGoalOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    target_amount: float
    current_amount: float
    created_at: datetime


class SavingsGoalCreateRequest(BaseModel):
    name: str
    target_amount: float


class SavingsGoalContributeRequest(BaseModel):
    amount: float  # positivo suma, negativo resta


class FixedExpenseOut(BaseModel):
    id: str
    name: str
    amount: float
    due_day: int
    checked: bool


class FixedExpenseCreateRequest(BaseModel):
    name: str
    amount: float
    due_day: int


class FixedExpenseUpdateRequest(BaseModel):
    name: str | None = None
    amount: float | None = None
    due_day: int | None = None


class IncomeOverrideRequest(BaseModel):
    monthly_amount: float | None  # null = borrar el override, volver a lo detectado


class FixedExpensesSummaryOut(BaseModel):
    estimated_income: float | None
    income_is_manual: bool
    total_fixed: float
    estimated_leftover: float | None


class MonthTotals(BaseModel):
    month: str  # "YYYY-MM"
    income: float
    expense: float
    net: float


class CategoryBreakdownItem(BaseModel):
    category: CategoryOut
    spent: float


class AnalysisSummary(BaseModel):
    month: str  # "YYYY-MM" del mes consultado
    income: float
    expense: float
    net: float
    no_computable: float  # traspasos entre cuentas propias, excluidos de income/expense
    budgeted_total: float  # suma de todos los presupuestos fijados
    budget_used_ratio: float | None  # expense / budgeted_total, None si no hay presupuestos
    last_six_months: list[MonthTotals]
    category_breakdown: list[CategoryBreakdownItem]  # solo gastos, del mes consultado
    income_breakdown: list[CategoryBreakdownItem]  # solo ingresos, del mes consultado
