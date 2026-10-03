"use client";

import Link from "next/link";
import { useCallback, useState } from "react";

import {
  Badge,
  Button,
  EmptyState,
  ErrorState,
  Field,
  LoadingState,
  Notice,
  Tabs,
} from "@/components/ui";
import { AccountsView } from "@/features/money/account-setup";
import { MoneyActivityList } from "@/features/money/money-activity-list";
import { useResource, type Resource } from "@/hooks/use-resource";
import { api } from "@/lib/api/client";
import type {
  IncomeStatement,
  JournalEntrySummary,
  Organization,
  Page,
  Project,
  TrialBalance,
} from "@/lib/api/types";
import { formatFinancialDate, formatMoney } from "@/lib/money";

type View = "overview" | "accounts" | "income" | "spending" | "transfers";

interface DateRange {
  startsOn: string;
  endsOn: string;
}

const views: Array<{ id: View; label: string }> = [
  { id: "overview", label: "Overview" },
  { id: "accounts", label: "Accounts" },
  { id: "income", label: "Income" },
  { id: "spending", label: "Spending" },
  { id: "transfers", label: "Transfers" },
];

const ACCOUNT_PAGE_SIZE = 12;
const ACTIVITY_PREVIEW_SIZE = 5;

function today(): string {
  return new Date().toISOString().slice(0, 10);
}

function monthStart(): string {
  const date = new Date();
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-01`;
}

export function MoneyWorkspace({ organization }: { organization: Organization }) {
  const [view, setView] = useState<View>("overview");
  const [range, setRange] = useState<DateRange>(() => ({
    startsOn: monthStart(),
    endsOn: today(),
  }));
  const [accountOffset, setAccountOffset] = useState(0);

  const loadReports = useCallback(
    () =>
      Promise.all([
        api.trialBalance(organization.id, { as_of: range.endsOn }),
        api.incomeStatement(organization.id, range.startsOn, range.endsOn),
      ]),
    [organization.id, range.endsOn, range.startsOn],
  );
  const reports = useResource(loadReports);

  const loadActivity = useCallback(
    () =>
      Promise.all([
        api.journalEntries(organization.id, 0, ACTIVITY_PREVIEW_SIZE),
        api.projects(organization.id, 0, 100),
      ]),
    [organization.id],
  );
  const activity = useResource(loadActivity);

  const loadAccounts = useCallback(
    () => api.accounts(organization.id, accountOffset, ACCOUNT_PAGE_SIZE),
    [accountOffset, organization.id],
  );
  const accounts = useResource(loadAccounts);

  function refreshAccounts() {
    accounts.reload();
    reports.reload();
  }

  return (
    <div className="money-workspace">
      <Tabs label="Money views" value={view} options={views} onChange={setView} />
      <div className="tab-panel money-tab-panel" role="tabpanel">
        {view === "overview" && (
          <MoneyOverview
            organization={organization}
            range={range}
            reports={reports}
            activity={activity}
            onRangeChange={setRange}
            onSelect={setView}
          />
        )}
        {view === "accounts" && (
          <AccountsView
            organization={organization}
            accounts={accounts}
            trialBalance={reports.data?.[0] ?? null}
            balanceLoading={reports.loading}
            offset={accountOffset}
            pageSize={ACCOUNT_PAGE_SIZE}
            onOffsetChange={setAccountOffset}
            onChanged={refreshAccounts}
          />
        )}
        {view === "income" && (
          <IncomeSpendingView
            kind="income"
            range={range}
            resource={reports}
            onRangeChange={setRange}
          />
        )}
        {view === "spending" && (
          <IncomeSpendingView
            kind="spending"
            range={range}
            resource={reports}
            onRangeChange={setRange}
          />
        )}
        {view === "transfers" && <TransfersView />}
      </div>
    </div>
  );
}

function MoneyOverview({
  organization,
  range,
  reports,
  activity,
  onRangeChange,
  onSelect,
}: {
  organization: Organization;
  range: DateRange;
  reports: Resource<[TrialBalance, IncomeStatement]>;
  activity: Resource<[Page<JournalEntrySummary>, Page<Project>]>;
  onRangeChange: (range: DateRange) => void;
  onSelect: (view: View) => void;
}) {
  if (reports.loading) return <MoneyOverviewLoading />;
  if (reports.error || !reports.data) {
    return (
      <ErrorState
        error={reports.error ?? new Error("Money information is unavailable.")}
        onRetry={reports.reload}
      />
    );
  }

  const [trialBalance, incomeStatement] = reports.data;
  return (
    <section className="money-overview">
      <div className="money-overview-heading">
        <div>
          <p className="eyebrow">Current picture</p>
          <h2>How the business is moving</h2>
          <p>
            Income and spending cover {formatFinancialDate(incomeStatement.starts_on)} through{" "}
            {formatFinancialDate(incomeStatement.ends_on)}. Account balances are as of{" "}
            {trialBalance.as_of ? formatFinancialDate(trialBalance.as_of) : "all posted dates"}.
          </p>
        </div>
        <Badge tone={trialBalance.balanced ? "success" : "warning"}>
          {trialBalance.balanced ? "Ledger balanced" : "Needs accounting review"}
        </Badge>
      </div>

      <DateRangeControl value={range} onApply={onRangeChange} />

      <div className="money-flow-summary" aria-label="Period money summary">
        <article>
          <span>Income</span>
          <strong>
            {formatMoney(
              incomeStatement.revenue,
              incomeStatement.currency,
              incomeStatement.minor_unit_digits,
            )}
          </strong>
          <button type="button" className="text-link" onClick={() => onSelect("income")}>
            Understand income
          </button>
        </article>
        <article>
          <span>Spending</span>
          <strong>
            {formatMoney(
              incomeStatement.expenses,
              incomeStatement.currency,
              incomeStatement.minor_unit_digits,
            )}
          </strong>
          <button type="button" className="text-link" onClick={() => onSelect("spending")}>
            Understand spending
          </button>
        </article>
      </div>

      <section className="money-section" aria-labelledby="account-balance-heading">
        <div className="section-heading compact-heading">
          <div>
            <p className="eyebrow">Accounts</p>
            <h2 id="account-balance-heading">Account balances</h2>
            <p>Each amount comes directly from the trial balance.</p>
          </div>
          <Button variant="quiet" onClick={() => onSelect("accounts")}>
            View all accounts
          </Button>
        </div>
        {trialBalance.accounts.length === 0 ? (
          <EmptyState
            icon="money"
            title="No money accounts yet"
            description="Create the accounts this business needs before recording financial activity."
          />
        ) : (
          <div className="money-account-preview">
            {trialBalance.accounts.slice(0, 6).map((account) => (
              <Link href={`/money/accounts/${account.account_id}`} key={account.account_id}>
                <span>
                  <small>{account.code}</small>
                  <strong>{account.name}</strong>
                  <em>{account.account_type}</em>
                </span>
                <AccountBalance
                  balance={account}
                  currency={trialBalance.currency}
                  minorUnitDigits={trialBalance.minor_unit_digits}
                />
              </Link>
            ))}
          </div>
        )}
      </section>

      <section className="money-section" aria-labelledby="recent-activity-heading">
        <div className="section-heading compact-heading">
          <div>
            <p className="eyebrow">Latest</p>
            <h2 id="recent-activity-heading">Recent activity</h2>
            <p>Posted entries stay linked to their accounting and audit detail.</p>
          </div>
          <Link className="text-link" href="/activity">
            View all activity
          </Link>
        </div>
        {activity.loading ? (
          <LoadingState label="Loading recent financial activity" />
        ) : activity.error || !activity.data ? (
          <ErrorState
            error={activity.error ?? new Error("Recent activity is unavailable.")}
            onRetry={activity.reload}
          />
        ) : (
          <MoneyActivityList
            entries={activity.data[0].items}
            projects={activity.data[1].items}
            currency={organization.currency}
            minorUnitDigits={organization.minor_unit_digits}
          />
        )}
      </section>
    </section>
  );
}

function MoneyOverviewLoading() {
  return (
    <div className="money-overview-loading">
      <LoadingState label="Loading Money overview" />
      <div className="money-loading-grid" aria-hidden="true">
        <span />
        <span />
      </div>
    </div>
  );
}

export function IncomeSpendingView({
  kind,
  range,
  resource,
  onRangeChange,
}: {
  kind: "income" | "spending";
  range: DateRange;
  resource: Resource<[TrialBalance, IncomeStatement]>;
  onRangeChange: (range: DateRange) => void;
}) {
  const label = kind === "income" ? "Income" : "Spending";
  const description =
    kind === "income"
      ? "Revenue recognized by the accounting engine for the selected financial dates."
      : "Expenses recognized by the accounting engine for the selected financial dates. Transfers are not included as spending by the UI.";

  return (
    <section className="money-view income-spending-view">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Business money</p>
          <h2>{label}</h2>
          <p>{description}</p>
        </div>
      </div>
      <DateRangeControl value={range} onApply={onRangeChange} />
      {resource.loading ? (
        <LoadingState label={`Loading ${label.toLowerCase()}`} />
      ) : resource.error || !resource.data ? (
        <ErrorState
          error={resource.error ?? new Error(`${label} is unavailable.`)}
          onRetry={resource.reload}
        />
      ) : (
        <IncomeSpendingResult kind={kind} report={resource.data[1]} />
      )}
    </section>
  );
}

function IncomeSpendingResult({
  kind,
  report,
}: {
  kind: "income" | "spending";
  report: IncomeStatement;
}) {
  const amount = kind === "income" ? report.revenue : report.expenses;
  return (
    <div className="income-spending-result">
      <div className="money-total-line">
        <span>
          <small>
            {formatFinancialDate(report.starts_on)} — {formatFinancialDate(report.ends_on)}
          </small>
          <strong>{formatMoney(amount, report.currency, report.minor_unit_digits)}</strong>
          <em>{kind === "income" ? "Total revenue" : "Total expenses"}</em>
        </span>
        <Badge tone="neutral">From posted ledger data</Badge>
      </div>
      <div className="money-detail-note">
        <div>
          <p className="eyebrow">Available detail</p>
          <h3>Follow the underlying activity</h3>
          <p>
            The current BUSINESS report API returns the authoritative aggregate for this period. It
            does not provide product categories, so Chatbooks does not invent a category breakdown
            or category filter here.
          </p>
        </div>
        <div className="money-detail-actions">
          <Link className="button button-secondary" href="/activity">
            Open activity
          </Link>
          <Link className="text-link" href="/reports">
            View full income statement
          </Link>
        </div>
      </div>
    </div>
  );
}

function DateRangeControl({
  value,
  onApply,
}: {
  value: DateRange;
  onApply: (range: DateRange) => void;
}) {
  const [startsOn, setStartsOn] = useState(value.startsOn);
  const [endsOn, setEndsOn] = useState(value.endsOn);
  const [error, setError] = useState("");

  function submit(event: React.FormEvent) {
    event.preventDefault();
    if (startsOn > endsOn) {
      setError("The start date must be on or before the end date.");
      return;
    }
    setError("");
    onApply({ startsOn, endsOn });
  }

  return (
    <form className="money-period-control surface" onSubmit={submit}>
      <div className="money-period-copy">
        <strong>Financial date range</strong>
        <small>Income and spending refresh only when you apply the range.</small>
      </div>
      <Field label="From">
        <input
          type="date"
          value={startsOn}
          max={endsOn}
          onChange={(event) => setStartsOn(event.target.value)}
        />
      </Field>
      <Field label="To">
        <input
          type="date"
          value={endsOn}
          min={startsOn}
          onChange={(event) => setEndsOn(event.target.value)}
        />
      </Field>
      <Button variant="secondary">Apply range</Button>
      {error && <span className="field-error money-period-error">{error}</span>}
    </form>
  );
}

function AccountBalance({
  balance,
  currency,
  minorUnitDigits,
}: {
  balance: TrialBalance["accounts"][number];
  currency: string;
  minorUnitDigits: number;
}) {
  const credit = balance.credit_balance !== 0;
  const value = credit ? balance.credit_balance : balance.debit_balance;
  return (
    <span className="aligned-numbers money-balance-value">
      <strong>{formatMoney(value, currency, minorUnitDigits)}</strong>
      <small>{value === 0 ? "Zero balance" : credit ? "Credit balance" : "Debit balance"}</small>
    </span>
  );
}

export function TransfersView() {
  return (
    <section className="money-view transfer-deferred">
      <EmptyState
        icon="money"
        title="Guided transfers are not enabled"
        description="The current BUSINESS API has no dedicated transfer workflow. Chatbooks will not imitate one with a normal expense or create unverified transfer records."
      />
      <Notice>
        Accountants may still use the structured proposal workflow when they know the required
        accounts and accounting treatment. Personal transfers and personal/business movements remain
        deferred.
      </Notice>
    </section>
  );
}
