export interface Category {
  id: string;
  name: string;
  system_icon_name: string;
  sort_order: number;
}

export interface LinkedAccount {
  account_uid: string;
  display_name: string;
  iban: string | null;
  last_synced_at: string | null;
  last_balance_amount: string | null;
  last_balance_currency: string | null;
  last_balance_refreshed_at: string | null;
  is_visible: boolean;
  is_balance_visible: boolean;
  last_sync_issue: string | null;
  color: string;
}

export interface BankConnection {
  id: string;
  aspsp_name: string;
  aspsp_country: string;
  linked_at: string;
  accounts: LinkedAccount[];
}

export interface Transaction {
  entry_reference: string;
  account_uid: string;
  account_color: string;
  category: Category | null;
  amount: number;
  currency: string;
  credit_debit_indicator: "CRDT" | "DBIT";
  booking_date: string;
  value_date: string | null;
  remittance_information: string;
  counterparty_name: string | null;
  merchant_category_code: string | null;
  status: string | null;
  is_user_categorized: boolean;
  has_debt_entries: boolean;
}

export interface ASPSP {
  name: string;
  country: string;
  logo?: string | null;
  bic?: string | null;
}

export interface SyncResult {
  account_uid: string;
  ok: boolean;
  error: string | null;
}

export interface AutoCategorizedItem {
  name: string;
  category_name: string;
  amount: number;
  currency: string;
}

export interface SyncResponse {
  results: SyncResult[];
  auto_categorized: AutoCategorizedItem[];
}

export interface Budget {
  category: Category;
  monthly_limit: number | null;
  effective_limit: number | null;
  rollover: boolean;
  spent_this_month: number;
}

export interface Alert {
  id: string;
  icon: string;
  title: string;
  subtitle: string;
}

export interface MonthTotals {
  month: string;
  income: number;
  expense: number;
  net: number;
}

export interface CategoryBreakdownItem {
  category: Category;
  spent: number;
}

export interface AnalysisSummary {
  month: string;
  income: number;
  expense: number;
  net: number;
  no_computable: number;
  budgeted_total: number;
  budget_used_ratio: number | null;
  last_six_months: MonthTotals[];
  category_breakdown: CategoryBreakdownItem[];
  income_breakdown: CategoryBreakdownItem[];
}

export interface Debtor {
  id: string;
  name: string;
  phone: string | null;
  created_at: string;
  balance: number;
}

export interface DebtEntry {
  id: string;
  amount: number;
  date: string;
  note: string | null;
  transaction_entry_reference: string | null;
}

export interface DebtorDetail {
  id: string;
  name: string;
  phone: string | null;
  created_at: string;
  balance: number;
  entries: DebtEntry[];
}

export interface Me {
  id: string;
  email: string;
  is_admin: boolean;
  created_at: string;
}

export interface RecurringCharge {
  id: string;
  name: string;
  amount: number;
  currency: string;
  frequency: "mensual" | "anual";
  occurrences: number;
  last_charge_date: string;
  next_expected_date: string;
  category_name: string | null;
}

export interface NetWorthPoint {
  date: string;
  total_amount: number;
}

export interface CategorizationRule {
  id: string;
  keyword: string;
  category: Category;
}

export interface SavingsGoal {
  id: string;
  name: string;
  target_amount: number;
  current_amount: number;
  linked_account_uid: string | null;
  linked_account_name: string | null;
  created_at: string;
}

export interface MatchedLoanPayment {
  entry_reference: string;
  booking_date: string;
  amount: number;
  description: string;
}

export interface Loan {
  id: string;
  name: string;
  credit_limit: number | null;
  balance: number;
  monthly_payment: number;
  tin: number | null;
  tae: number | null;
  next_payment_date: string | null;
  updated_at: string;
  matched_transaction: MatchedLoanPayment | null;
}

export interface FixedExpense {
  id: string;
  name: string;
  amount: number;
  due_day: number;
  checked: boolean;
}

export interface FixedExpensesSummary {
  estimated_income: number | null;
  income_is_manual: boolean;
  total_fixed: number;
  estimated_leftover: number | null;
}

export interface AdminUser {
  id: string;
  email: string;
  is_admin: boolean;
  created_at: string;
  bank_connections_count: number;
  transactions_count: number;
  debtors_count: number;
}
