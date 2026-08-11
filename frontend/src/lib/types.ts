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

export interface Budget {
  category: Category;
  monthly_limit: number | null;
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
}

export interface Debtor {
  id: string;
  name: string;
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

export interface AdminUser {
  id: string;
  email: string;
  is_admin: boolean;
  created_at: string;
  bank_connections_count: number;
  transactions_count: number;
  debtors_count: number;
}
