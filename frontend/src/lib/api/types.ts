export type OrganizationRole = "OWNER" | "ADMIN" | "ACCOUNTANT" | "MEMBER" | "VIEWER";
export type ProjectStatus = "planned" | "active" | "completed" | "cancelled";
export type AccountType = "asset" | "liability" | "equity" | "revenue" | "expense";

export interface User {
  id: string;
  name: string;
  username: string;
}

export interface TokenResponse {
  token_type: "bearer";
  expires_at: string;
  user: User;
}

export interface Organization {
  id: string;
  name: string;
  currency: string;
  minor_unit_digits: number;
  role: OrganizationRole;
}

export interface Page<T> {
  items: T[];
  total: number;
  offset: number;
  limit: number;
}

export interface Project {
  id: string;
  organization_id: string;
  name: string;
  description: string;
  client: string | null;
  expected_revenue: number | null;
  budget: number | null;
  starts_on: string | null;
  ends_on: string | null;
  status: ProjectStatus;
}

export type ProjectPayload = Omit<Project, "id" | "organization_id">;

export interface Account {
  id: string;
  organization_id: string;
  code: string;
  name: string;
  account_type: AccountType;
  active: boolean;
}

export interface Period {
  id: string;
  organization_id: string;
  name: string;
  starts_on: string;
  ends_on: string;
  locked: boolean;
}

export interface ProposalLine {
  position: number;
  account_id: string;
  code: string;
  name: string;
  debit: number;
  credit: number;
  project_id: string | null;
}

export interface Proposal {
  id: string;
  organization_id: string;
  entry_date: string;
  description: string;
  document_id: string | null;
  reverses_entry_id: string | null;
  version: number;
  state: string;
  lines: ProposalLine[];
  posted_entry_id: string | null;
  status: string;
  lifecycle_state: "PROPOSED" | "VALIDATED" | "CONFIRMED" | "POSTED";
  currency: string;
  minor_unit_digits: number;
}

export interface Validation {
  id: string;
  transaction_id: string;
  fingerprint: string;
  debit_total: number;
  credit_total: number;
}

export interface Confirmation {
  id: string;
  validation_id: string;
  actor_id: string;
  proposal_id: string;
  proposal_version: number;
  confirmed_at: string;
  confirmation_request_id: string;
}

export interface JournalLine {
  position: number;
  account_id: string;
  code: string;
  account_name: string;
  account_type: AccountType;
  debit: number;
  credit: number;
  project_id: string | null;
}

export interface JournalEntrySummary {
  id: string;
  organization_id: string;
  transaction_id: string;
  confirmation_id: string;
  period_id: string;
  entry_date: string;
  description: string;
  reverses_entry_id: string | null;
  state: "posted";
  debit_total: number;
  credit_total: number;
  line_count: number;
  project_ids: string[];
}

export interface JournalEntry extends JournalEntrySummary {
  lines: JournalLine[];
}

export interface LedgerLine {
  entry_id: string;
  transaction_id: string;
  entry_date: string;
  description: string;
  reverses_entry_id: string | null;
  line_id: string;
  position: number;
  account_id: string;
  code: string;
  account_name: string;
  account_type: AccountType;
  debit: number;
  credit: number;
  project_id: string | null;
}

export interface Balance {
  account_id: string;
  code: string;
  name: string;
  account_type: AccountType;
  debits: number;
  credits: number;
  net_debit: number;
  debit_balance: number;
  credit_balance: number;
}

export interface TrialBalance {
  currency: string;
  minor_unit_digits: number;
  as_of: string | null;
  project_id: string | null;
  accounts: Balance[];
  total_debits: number;
  total_credits: number;
  balanced: boolean;
}

export interface IncomeStatement {
  currency: string;
  minor_unit_digits: number;
  starts_on: string;
  ends_on: string;
  revenue: number;
  expenses: number;
  net_income: number;
}

export interface BalanceSheet {
  currency: string;
  minor_unit_digits: number;
  as_of: string;
  assets: number;
  liabilities: number;
  recorded_equity: number;
  unclosed_earnings: number;
  total_equity: number;
  balanced: boolean;
}

export interface CashFlow {
  currency: string;
  minor_unit_digits: number;
  starts_on: string;
  ends_on: string;
  cash_accounts: Account[];
  movements: LedgerLine[];
  total_inflows: number;
  total_outflows: number;
  net_change: number;
  classification: "unclassified_cash_movements";
}

export interface AuditEvent {
  sequence: number;
  organization_id: string;
  actor_id: string;
  occurred_at: string;
  event_type: string;
  entity_type: string;
  entity_id: string;
  previous_state: Record<string, unknown> | null;
  new_state: Record<string, unknown> | null;
  metadata: Record<string, unknown>;
}

export interface ApiErrorBody {
  error: string;
  message: string;
  request_id: string;
  details: unknown;
}
