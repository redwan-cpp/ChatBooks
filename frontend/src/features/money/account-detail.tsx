"use client";

import Link from "next/link";

import { Badge, Button, Notice } from "@/components/ui";
import type { Account, Balance, Organization, TrialBalance } from "@/lib/api/types";
import { formatFinancialDate, formatMoney } from "@/lib/money";
import { allows } from "@/lib/permissions";

const typeLabels: Record<Account["account_type"], string> = {
  asset: "Asset",
  liability: "Liability",
  equity: "Equity",
  revenue: "Revenue",
  expense: "Expense",
};

export function AccountDetail({
  account,
  balance,
  report,
  organization,
  updating = false,
  onToggle,
}: {
  account: Account;
  balance: Balance | null;
  report: TrialBalance;
  organization: Organization;
  updating?: boolean;
  onToggle?: () => void;
}) {
  const isCredit = balance ? balance.credit_balance !== 0 : false;
  const currentBalance = balance
    ? isCredit
      ? balance.credit_balance
      : balance.debit_balance
    : null;
  const canManage = allows(organization.role, "manage_account");

  return (
    <div className="account-detail">
      <section className="account-detail-hero">
        <div>
          <span className="account-detail-code">{account.code}</span>
          <h2>{account.name}</h2>
          <p>
            {typeLabels[account.account_type]} account · Balance as of{" "}
            {report.as_of ? formatFinancialDate(report.as_of) : "all posted dates"}
          </p>
        </div>
        <div className="account-detail-amount aligned-numbers">
          <small>Current balance</small>
          <strong>
            {currentBalance === null
              ? "Unavailable"
              : formatMoney(currentBalance, report.currency, report.minor_unit_digits)}
          </strong>
          {currentBalance !== null && (
            <span>
              {currentBalance === 0
                ? "Zero balance"
                : isCredit
                  ? "Credit balance"
                  : "Debit balance"}
            </span>
          )}
        </div>
      </section>

      <section className="account-detail-metadata" aria-label="Account information">
        <div>
          <small>Status</small>
          <Badge tone={account.active ? "success" : "neutral"}>
            {account.active ? "Active" : "Inactive"}
          </Badge>
        </div>
        <div>
          <small>Account type</small>
          <strong>{typeLabels[account.account_type]}</strong>
        </div>
        <div>
          <small>Account code</small>
          <strong>{account.code}</strong>
        </div>
        {canManage && onToggle && (
          <Button variant="secondary" disabled={updating} onClick={onToggle}>
            {updating ? "Updating…" : account.active ? "Deactivate account" : "Reactivate account"}
          </Button>
        )}
      </section>

      <details className="account-disclosure">
        <summary>
          <span>
            <strong>Accounting detail</strong>
            <small>Reveal the ledger totals behind this balance</small>
          </span>
          <span>Show detail</span>
        </summary>
        <dl>
          <div>
            <dt>Total debits</dt>
            <dd>
              {balance
                ? formatMoney(balance.debits, report.currency, report.minor_unit_digits)
                : "Unavailable"}
            </dd>
          </div>
          <div>
            <dt>Total credits</dt>
            <dd>
              {balance
                ? formatMoney(balance.credits, report.currency, report.minor_unit_digits)
                : "Unavailable"}
            </dd>
          </div>
          <div>
            <dt>Net debit</dt>
            <dd>
              {balance
                ? formatMoney(balance.net_debit, report.currency, report.minor_unit_digits)
                : "Unavailable"}
            </dd>
          </div>
        </dl>
      </details>

      <section className="account-activity-link">
        <div>
          <p className="eyebrow">Activity</p>
          <h3>Review posted financial activity</h3>
          <p>
            The current BUSINESS API does not provide an account-specific activity filter. Open the
            full activity record to inspect entries and their account lines.
          </p>
        </div>
        <Link className="button button-secondary" href="/activity">
          Open activity
        </Link>
      </section>

      {!balance && (
        <Notice>
          This account has no balance row in the current trial balance response. Chatbooks does not
          infer an amount that the report did not return.
        </Notice>
      )}
    </div>
  );
}
