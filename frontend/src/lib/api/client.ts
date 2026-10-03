import type {
  Account,
  AuditEvent,
  BalanceSheet,
  CashFlow,
  Confirmation,
  IncomeStatement,
  JournalEntry,
  JournalEntrySummary,
  LedgerLine,
  Organization,
  Page,
  Period,
  Project,
  ProjectPayload,
  Proposal,
  TokenResponse,
  TrialBalance,
  User,
  Validation,
} from "./types";

const BASE = "/api/chatbook";

export class ApiError extends Error {
  constructor(
    readonly code: string,
    message: string,
    readonly status: number,
    readonly requestId?: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

interface RequestOptions extends Omit<RequestInit, "body"> {
  body?: unknown;
  idempotencyKey?: string;
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const headers = new Headers(options.headers);
  headers.set("Accept", "application/json");
  if (options.body !== undefined) headers.set("Content-Type", "application/json");
  if (options.idempotencyKey) headers.set("Idempotency-Key", options.idempotencyKey);
  const response = await fetch(`${BASE}${path}`, {
    ...options,
    cache: "no-store",
    headers,
    body: options.body === undefined ? undefined : JSON.stringify(options.body),
  });
  if (!response.ok) {
    const fallback = { error: "request_failed", message: "The request could not be completed." };
    const payload = (await response.json().catch(() => fallback)) as {
      error?: string;
      message?: string;
      request_id?: string;
    };
    throw new ApiError(
      payload.error ?? fallback.error,
      payload.message ?? fallback.message,
      response.status,
      payload.request_id,
    );
  }
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

function query(values: Record<string, string | number | string[] | null | undefined>): string {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(values)) {
    if (value === null || value === undefined || value === "") continue;
    if (Array.isArray(value)) value.forEach((item) => params.append(key, item));
    else params.set(key, String(value));
  }
  const encoded = params.toString();
  return encoded ? `?${encoded}` : "";
}

export const api = {
  register: (payload: { name: string; username: string; password: string }) =>
    request<User>("/auth/register", { method: "POST", body: payload }),
  login: (payload: { username: string; password: string }) =>
    request<TokenResponse>("/auth/token", { method: "POST", body: payload }),
  me: () => request<User>("/auth/me"),
  logout: () => request<void>("/auth/logout", { method: "POST" }),
  organizations: () => request<Organization[]>("/organizations"),
  createOrganization: (payload: { name: string; currency: string; minor_unit_digits: number }) =>
    request<Organization>("/organizations", { method: "POST", body: payload }),
  projects: (organizationId: string, offset = 0, limit = 50) =>
    request<Page<Project>>(`/organizations/${organizationId}/projects${query({ offset, limit })}`),
  project: (organizationId: string, projectId: string) =>
    request<Project>(`/organizations/${organizationId}/projects/${projectId}`),
  createProject: (organizationId: string, payload: ProjectPayload) =>
    request<Project>(`/organizations/${organizationId}/projects`, {
      method: "POST",
      body: payload,
    }),
  updateProject: (organizationId: string, projectId: string, payload: Partial<ProjectPayload>) =>
    request<Project>(`/organizations/${organizationId}/projects/${projectId}`, {
      method: "PATCH",
      body: payload,
    }),
  accounts: (organizationId: string, offset = 0, limit = 100) =>
    request<Page<Account>>(`/organizations/${organizationId}/accounts${query({ offset, limit })}`),
  account: (organizationId: string, accountId: string) =>
    request<Account>(`/organizations/${organizationId}/accounts/${accountId}`),
  createAccount: (
    organizationId: string,
    payload: { code: string; name: string; account_type: Account["account_type"] },
  ) =>
    request<Account>(`/organizations/${organizationId}/accounts`, {
      method: "POST",
      body: payload,
    }),
  updateAccount: (organizationId: string, accountId: string, active: boolean) =>
    request<Account>(`/organizations/${organizationId}/accounts/${accountId}`, {
      method: "PATCH",
      body: { active },
    }),
  periods: (organizationId: string) =>
    request<Period[]>(`/organizations/${organizationId}/periods`),
  createPeriod: (
    organizationId: string,
    payload: { name: string; starts_on: string; ends_on: string },
  ) =>
    request<Period>(`/organizations/${organizationId}/periods`, {
      method: "POST",
      body: payload,
    }),
  lockPeriod: (organizationId: string, periodId: string) =>
    request<Period>(`/organizations/${organizationId}/periods/${periodId}/lock`, {
      method: "POST",
    }),
  journalEntries: (organizationId: string, offset = 0, limit = 20) =>
    request<Page<JournalEntrySummary>>(
      `/organizations/${organizationId}/journal-entries${query({ offset, limit })}`,
    ),
  journalEntry: (organizationId: string, entryId: string) =>
    request<JournalEntry>(`/organizations/${organizationId}/journal-entries/${entryId}`),
  generalLedger: (
    organizationId: string,
    filters: {
      starts_on?: string;
      as_of?: string;
      project_id?: string;
      offset?: number;
      limit?: number;
    } = {},
  ) =>
    request<Page<LedgerLine>>(
      `/organizations/${organizationId}/reports/general-ledger${query(filters)}`,
    ),
  trialBalance: (organizationId: string, filters: { as_of?: string; project_id?: string } = {}) =>
    request<TrialBalance>(
      `/organizations/${organizationId}/reports/trial-balance${query(filters)}`,
    ),
  incomeStatement: (organizationId: string, startsOn: string, endsOn: string) =>
    request<IncomeStatement>(
      `/organizations/${organizationId}/reports/income-statement${query({ starts_on: startsOn, ends_on: endsOn })}`,
    ),
  balanceSheet: (organizationId: string, asOf: string) =>
    request<BalanceSheet>(
      `/organizations/${organizationId}/reports/balance-sheet${query({ as_of: asOf })}`,
    ),
  cashFlow: (organizationId: string, startsOn: string, endsOn: string, accountIds: string[]) =>
    request<CashFlow>(
      `/organizations/${organizationId}/reports/cash-flow${query({ starts_on: startsOn, ends_on: endsOn, cash_account_id: accountIds })}`,
    ),
  auditEvents: (organizationId: string, offset = 0, limit = 50, entityId?: string) =>
    request<Page<AuditEvent>>(
      `/organizations/${organizationId}/audit-events${query({ offset, limit, entity_id: entityId })}`,
    ),
  createProposal: (
    organizationId: string,
    payload: {
      entry_date: string;
      description: string;
      document_id?: string | null;
      lines: Array<{
        account_id: string;
        debit: number;
        credit: number;
        project_id?: string | null;
      }>;
    },
  ) =>
    request<Proposal>(`/organizations/${organizationId}/proposals`, {
      method: "POST",
      body: payload,
    }),
  proposal: (organizationId: string, proposalId: string) =>
    request<Proposal>(`/organizations/${organizationId}/proposals/${proposalId}`),
  validateProposal: (organizationId: string, proposalId: string) =>
    request<Validation>(`/organizations/${organizationId}/proposals/${proposalId}/validate`, {
      method: "POST",
    }),
  confirmProposal: (
    organizationId: string,
    proposalId: string,
    validationId: string,
    proposalVersion: number,
    idempotencyKey: string,
  ) =>
    request<Confirmation>(`/organizations/${organizationId}/proposals/${proposalId}/confirm`, {
      method: "POST",
      idempotencyKey,
      body: { validation_id: validationId, proposal_version: proposalVersion, accepted: true },
    }),
  postProposal: (
    organizationId: string,
    proposalId: string,
    confirmationId: string,
    idempotencyKey: string,
  ) =>
    request<{ entry_id: string }>(`/organizations/${organizationId}/proposals/${proposalId}/post`, {
      method: "POST",
      idempotencyKey,
      body: { confirmation_id: confirmationId },
    }),
  createReversal: (
    organizationId: string,
    entryId: string,
    payload: { entry_date: string; reason: string },
  ) =>
    request<Proposal>(`/organizations/${organizationId}/journal-entries/${entryId}/reversals`, {
      method: "POST",
      body: payload,
    }),
};
