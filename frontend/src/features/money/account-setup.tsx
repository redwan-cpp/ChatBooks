"use client";

import Link from "next/link";
import { useMemo, useState } from "react";

import {
  Badge,
  Button,
  EmptyState,
  ErrorState,
  Field,
  LoadingState,
  Notice,
} from "@/components/ui";
import type { Resource } from "@/hooks/use-resource";
import { api } from "@/lib/api/client";
import type { Account, AccountType, Organization, Page, TrialBalance } from "@/lib/api/types";
import { formatMoney } from "@/lib/money";
import { allows } from "@/lib/permissions";

const accountTypeLabels: Record<AccountType, string> = {
  asset: "Asset",
  liability: "Liability",
  equity: "Equity",
  revenue: "Revenue",
  expense: "Expense",
};

type StatusFilter = "all" | "active" | "inactive";

export function AccountsView({
  organization,
  accounts,
  trialBalance,
  balanceLoading,
  offset,
  pageSize,
  onOffsetChange,
  onChanged,
}: {
  organization: Organization;
  accounts: Resource<Page<Account>>;
  trialBalance: TrialBalance | null;
  balanceLoading: boolean;
  offset: number;
  pageSize: number;
  onOffsetChange: (offset: number) => void;
  onChanged: () => void;
}) {
  const [showForm, setShowForm] = useState(false);
  const [code, setCode] = useState("");
  const [name, setName] = useState("");
  const [type, setType] = useState<AccountType>("asset");
  const [query, setQuery] = useState("");
  const [typeFilter, setTypeFilter] = useState<"all" | AccountType>("all");
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const [updatingId, setUpdatingId] = useState("");
  const canManage = allows(organization.role, "manage_account");

  const visibleAccounts = useMemo(() => {
    const normalizedQuery = query.trim().toLocaleLowerCase();
    return (accounts.data?.items ?? []).filter((account) => {
      const matchesQuery =
        !normalizedQuery ||
        account.name.toLocaleLowerCase().includes(normalizedQuery) ||
        account.code.toLocaleLowerCase().includes(normalizedQuery);
      const matchesType = typeFilter === "all" || account.account_type === typeFilter;
      const matchesStatus =
        statusFilter === "all" || (statusFilter === "active" ? account.active : !account.active);
      return matchesQuery && matchesType && matchesStatus;
    });
  }, [accounts.data?.items, query, statusFilter, typeFilter]);

  async function create(event: React.FormEvent) {
    event.preventDefault();
    setSaving(true);
    setError("");
    try {
      await api.createAccount(organization.id, { code, name, account_type: type });
      setCode("");
      setName("");
      setShowForm(false);
      onChanged();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not create the account.");
    } finally {
      setSaving(false);
    }
  }

  async function toggle(account: Account) {
    setUpdatingId(account.id);
    setError("");
    try {
      await api.updateAccount(organization.id, account.id, !account.active);
      onChanged();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not update the account.");
    } finally {
      setUpdatingId("");
    }
  }

  const hasFilters = query.trim() !== "" || typeFilter !== "all" || statusFilter !== "all";
  const page = accounts.data;
  const pageStart = page && page.total > 0 ? page.offset + 1 : 0;
  const pageEnd = page ? Math.min(page.offset + page.items.length, page.total) : 0;

  return (
    <section className="money-view accounts-view">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Business money</p>
          <h2>Accounts</h2>
          <p>See each account’s current ledger balance and reveal accounting detail when needed.</p>
        </div>
        {canManage && (
          <Button variant="secondary" onClick={() => setShowForm((value) => !value)}>
            {showForm ? "Cancel" : "Add account"}
          </Button>
        )}
      </div>

      {error && <Notice tone="error">{error}</Notice>}
      {showForm && (
        <form className="account-create-form surface" onSubmit={create}>
          <div>
            <strong>Add a business account</strong>
            <small>The accounting engine validates the account before it is saved.</small>
          </div>
          <Field label="Code">
            <input required value={code} onChange={(event) => setCode(event.target.value)} />
          </Field>
          <Field label="Name">
            <input required value={name} onChange={(event) => setName(event.target.value)} />
          </Field>
          <Field label="Account type">
            <select value={type} onChange={(event) => setType(event.target.value as AccountType)}>
              {Object.entries(accountTypeLabels).map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
          </Field>
          <Button disabled={saving}>{saving ? "Adding…" : "Add account"}</Button>
        </form>
      )}

      <div className="account-filters" aria-label="Account filters">
        <Field label="Find on this page">
          <input
            type="search"
            value={query}
            placeholder="Name or code"
            onChange={(event) => setQuery(event.target.value)}
          />
        </Field>
        <Field label="Account type">
          <select
            value={typeFilter}
            onChange={(event) => setTypeFilter(event.target.value as "all" | AccountType)}
          >
            <option value="all">All types</option>
            {Object.entries(accountTypeLabels).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </Field>
        <Field label="Status">
          <select
            value={statusFilter}
            onChange={(event) => setStatusFilter(event.target.value as StatusFilter)}
          >
            <option value="all">All statuses</option>
            <option value="active">Active</option>
            <option value="inactive">Inactive</option>
          </select>
        </Field>
        <p>Filters apply to the loaded page. They do not change balances or report totals.</p>
      </div>

      {accounts.loading ? (
        <LoadingState label="Loading accounts" />
      ) : accounts.error || !page ? (
        <ErrorState
          error={accounts.error ?? new Error("Accounts are unavailable.")}
          onRetry={accounts.reload}
        />
      ) : page.items.length === 0 ? (
        <EmptyState
          icon="money"
          title="No accounts yet"
          description="An authorized user can add the accounts needed for proposals and reports."
        />
      ) : visibleAccounts.length === 0 ? (
        <EmptyState
          icon="money"
          title="No accounts match these filters"
          description={
            hasFilters
              ? "Clear or change the filters to see other accounts on this page."
              : "There are no accounts on this page."
          }
        />
      ) : (
        <div className="account-list">
          {visibleAccounts.map((account) => {
            const balance = trialBalance?.accounts.find((item) => item.account_id === account.id);
            return (
              <article className="account-row" key={account.id}>
                <Link href={`/money/accounts/${account.id}`} aria-label={`View ${account.name}`}>
                  <span className="account-identity">
                    <small>{account.code}</small>
                    <strong>{account.name}</strong>
                    <em>{accountTypeLabels[account.account_type]}</em>
                  </span>
                  <span className="account-row-balance aligned-numbers">
                    {balanceLoading ? (
                      <small>Loading balance…</small>
                    ) : balance && trialBalance ? (
                      <AccountBalanceValue balance={balance} report={trialBalance} />
                    ) : (
                      <small>Balance unavailable</small>
                    )}
                  </span>
                </Link>
                <div className="account-row-actions">
                  <Badge tone={account.active ? "success" : "neutral"}>
                    {account.active ? "Active" : "Inactive"}
                  </Badge>
                  {canManage && (
                    <Button
                      variant="quiet"
                      disabled={updatingId === account.id}
                      onClick={() => void toggle(account)}
                    >
                      {updatingId === account.id
                        ? "Updating…"
                        : account.active
                          ? "Deactivate"
                          : "Reactivate"}
                    </Button>
                  )}
                </div>
              </article>
            );
          })}
        </div>
      )}

      {page && page.total > 0 && (
        <nav className="account-pagination" aria-label="Account pages">
          <p>
            Showing {pageStart}–{pageEnd} of {page.total}
          </p>
          <div>
            <Button
              variant="secondary"
              disabled={offset === 0 || accounts.loading}
              onClick={() => onOffsetChange(Math.max(0, offset - pageSize))}
            >
              Previous
            </Button>
            <Button
              variant="secondary"
              disabled={offset + pageSize >= page.total || accounts.loading}
              onClick={() => onOffsetChange(offset + pageSize)}
            >
              Next
            </Button>
          </div>
        </nav>
      )}
    </section>
  );
}

function AccountBalanceValue({
  balance,
  report,
}: {
  balance: TrialBalance["accounts"][number];
  report: TrialBalance;
}) {
  const isCredit = balance.credit_balance !== 0;
  const amount = isCredit ? balance.credit_balance : balance.debit_balance;
  return (
    <>
      <strong>{formatMoney(amount, report.currency, report.minor_unit_digits)}</strong>
      <small>{amount === 0 ? "Zero balance" : isCredit ? "Credit balance" : "Debit balance"}</small>
    </>
  );
}
