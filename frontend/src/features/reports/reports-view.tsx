"use client";

import { useCallback, useMemo, useState } from "react";

import {
  Badge,
  Button,
  EmptyState,
  ErrorState,
  Field,
  LoadingState,
  Notice,
} from "@/components/ui";
import { useFinancialSpace } from "@/features/context/financial-space-provider";
import { useResource } from "@/hooks/use-resource";
import { api } from "@/lib/api/client";
import type {
  Account,
  BalanceSheet,
  CashFlow,
  IncomeStatement,
  LedgerLine,
  Page,
  TrialBalance,
} from "@/lib/api/types";
import { formatFinancialDate, formatMoney } from "@/lib/money";

type ReportKind = "income" | "balance" | "cash" | "trial" | "ledger";

function today(): string {
  return new Date().toISOString().slice(0, 10);
}
function monthStart(): string {
  const date = new Date();
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-01`;
}

export function ReportsView() {
  const { organization } = useFinancialSpace();
  const [kind, setKind] = useState<ReportKind>("income");
  const [startsOn, setStartsOn] = useState(monthStart);
  const [endsOn, setEndsOn] = useState(today);
  const [asOf, setAsOf] = useState(today);
  const [cashAccountIds, setCashAccountIds] = useState<string[]>([]);
  const [ledgerOffset, setLedgerOffset] = useState(0);
  const organizationId = organization?.id ?? "";
  const loadAccounts = useCallback(() => api.accounts(organizationId, 0, 100), [organizationId]);
  const accountResource = useResource(loadAccounts);
  const load = useCallback(async () => {
    switch (kind) {
      case "income":
        return {
          kind,
          value: await api.incomeStatement(organizationId, startsOn, endsOn),
        } as const;
      case "balance":
        return { kind, value: await api.balanceSheet(organizationId, asOf) } as const;
      case "trial":
        return { kind, value: await api.trialBalance(organizationId, { as_of: asOf }) } as const;
      case "ledger":
        return {
          kind,
          value: await api.generalLedger(organizationId, {
            starts_on: startsOn,
            as_of: endsOn,
            offset: ledgerOffset,
            limit: 100,
          }),
        } as const;
      case "cash":
        return cashAccountIds.length === 0
          ? ({ kind, value: null } as const)
          : ({
              kind,
              value: await api.cashFlow(organizationId, startsOn, endsOn, cashAccountIds),
            } as const);
    }
  }, [asOf, cashAccountIds, endsOn, kind, ledgerOffset, organizationId, startsOn]);
  const report = useResource(load);
  const accounts = accountResource.data?.items ?? [];
  const reportTabs: Array<{ id: ReportKind; label: string }> = [
    { id: "income", label: "Income" },
    { id: "balance", label: "Balance sheet" },
    { id: "cash", label: "Cash flow" },
    { id: "trial", label: "Trial balance" },
    { id: "ledger", label: "General ledger" },
  ];
  if (!organization) return null;
  const currency = organization.currency;
  const digits = organization.minor_unit_digits;

  return (
    <div className="section-stack">
      <div className="report-tabs" role="tablist" aria-label="Financial reports">
        {reportTabs.map((tab) => (
          <button
            key={tab.id}
            role="tab"
            aria-selected={kind === tab.id}
            className={kind === tab.id ? "active" : ""}
            onClick={() => setKind(tab.id)}
          >
            {tab.label}
          </button>
        ))}
      </div>
      <section className="surface report-controls">
        {kind === "balance" || kind === "trial" ? (
          <Field label="As of">
            <input type="date" value={asOf} onChange={(event) => setAsOf(event.target.value)} />
          </Field>
        ) : (
          <>
            <Field label="From">
              <input
                type="date"
                value={startsOn}
                onChange={(event) => setStartsOn(event.target.value)}
              />
            </Field>
            <Field label="To">
              <input
                type="date"
                value={endsOn}
                onChange={(event) => setEndsOn(event.target.value)}
              />
            </Field>
          </>
        )}
        <Button variant="secondary" onClick={report.reload}>
          Refresh
        </Button>
      </section>
      {kind === "cash" && (
        <CashAccountPicker
          accounts={accounts}
          selected={cashAccountIds}
          onChange={setCashAccountIds}
          loading={accountResource.loading}
        />
      )}
      {report.loading ? (
        <LoadingState label="Loading report" />
      ) : report.error ? (
        <ErrorState error={report.error} onRetry={report.reload} />
      ) : report.data ? (
        <>
          <ReportResult result={report.data} currency={currency} digits={digits} />
          {report.data.kind === "ledger" && report.data.value.total > report.data.value.limit && (
            <LedgerPagination
              page={report.data.value}
              offset={ledgerOffset}
              onOffset={setLedgerOffset}
            />
          )}
        </>
      ) : null}
    </div>
  );
}

function LedgerPagination({
  page,
  offset,
  onOffset,
}: {
  page: Page<LedgerLine>;
  offset: number;
  onOffset: (value: number) => void;
}) {
  return (
    <div className="pagination">
      <button disabled={offset === 0} onClick={() => onOffset(Math.max(0, offset - page.limit))}>
        Previous
      </button>
      <span>
        {offset + 1}–{Math.min(offset + page.limit, page.total)} of {page.total}
      </span>
      <button
        disabled={offset + page.limit >= page.total}
        onClick={() => onOffset(offset + page.limit)}
      >
        Next
      </button>
    </div>
  );
}

function CashAccountPicker({
  accounts,
  selected,
  onChange,
  loading,
}: {
  accounts: Account[];
  selected: string[];
  onChange: (ids: string[]) => void;
  loading: boolean;
}) {
  const sorted = useMemo(
    () => accounts.filter((account) => account.active && account.account_type === "asset"),
    [accounts],
  );
  return (
    <section className="surface cash-picker">
      <div>
        <p className="eyebrow">Explicit classification</p>
        <h2>Choose cash accounts</h2>
        <p>Chatbooks does not infer which asset accounts represent cash.</p>
      </div>
      {loading ? (
        <LoadingState label="Loading accounts" />
      ) : sorted.length === 0 ? (
        <Notice tone="warning">Create an account before requesting cash movements.</Notice>
      ) : (
        <div className="choice-grid">
          {sorted.map((account) => (
            <label className="check-row" key={account.id}>
              <input
                type="checkbox"
                checked={selected.includes(account.id)}
                onChange={(event) =>
                  onChange(
                    event.target.checked
                      ? [...selected, account.id]
                      : selected.filter((id) => id !== account.id),
                  )
                }
              />
              <span>
                {account.code} · {account.name}
                <small>{account.account_type}</small>
              </span>
            </label>
          ))}
        </div>
      )}
    </section>
  );
}

type ReportResultValue =
  | { kind: "income"; value: IncomeStatement }
  | { kind: "balance"; value: BalanceSheet }
  | { kind: "cash"; value: CashFlow | null }
  | { kind: "trial"; value: TrialBalance }
  | { kind: "ledger"; value: Page<LedgerLine> };

export function ReportResult({
  result,
  currency,
  digits,
}: {
  result: ReportResultValue;
  currency: string;
  digits: number;
}) {
  if (result.kind === "cash" && result.value === null) {
    return (
      <EmptyState
        icon="reports"
        title="Choose cash accounts"
        description="Select the accounts that should be included, then the accounting engine can return their movements."
      />
    );
  }
  if (result.kind === "income") {
    const value = result.value;
    return (
      <ReportSurface
        title="Income statement"
        subtitle={`${formatFinancialDate(value.starts_on)} — ${formatFinancialDate(value.ends_on)}`}
      >
        <dl className="report-lines">
          <div>
            <dt>Revenue</dt>
            <dd>{formatMoney(value.revenue, currency, digits)}</dd>
          </div>
          <div>
            <dt>Expenses</dt>
            <dd>{formatMoney(value.expenses, currency, digits)}</dd>
          </div>
          <div className="report-total">
            <dt>Net income</dt>
            <dd>{formatMoney(value.net_income, currency, digits)}</dd>
          </div>
        </dl>
      </ReportSurface>
    );
  }
  if (result.kind === "balance") {
    const value = result.value;
    return (
      <ReportSurface
        title="Balance sheet"
        subtitle={`As of ${formatFinancialDate(value.as_of)}`}
        status={
          <Badge tone={value.balanced ? "success" : "warning"}>
            {value.balanced ? "Balanced" : "Needs review"}
          </Badge>
        }
      >
        <dl className="report-lines">
          <div>
            <dt>Assets</dt>
            <dd>{formatMoney(value.assets, currency, digits)}</dd>
          </div>
          <div>
            <dt>Liabilities</dt>
            <dd>{formatMoney(value.liabilities, currency, digits)}</dd>
          </div>
          <div>
            <dt>Recorded equity</dt>
            <dd>{formatMoney(value.recorded_equity, currency, digits)}</dd>
          </div>
          <div>
            <dt>Unclosed earnings</dt>
            <dd>{formatMoney(value.unclosed_earnings, currency, digits)}</dd>
          </div>
          <div className="report-total">
            <dt>Total equity</dt>
            <dd>{formatMoney(value.total_equity, currency, digits)}</dd>
          </div>
        </dl>
      </ReportSurface>
    );
  }
  if (result.kind === "trial") {
    const value = result.value;
    return (
      <ReportSurface
        title="Trial balance"
        subtitle={value.as_of ? `As of ${formatFinancialDate(value.as_of)}` : "All posted activity"}
        status={
          <Badge tone={value.balanced ? "success" : "warning"}>
            {value.balanced ? "Balanced" : "Needs review"}
          </Badge>
        }
      >
        <div className="report-table">
          <div className="report-table-head">
            <span>Account</span>
            <span>Debit</span>
            <span>Credit</span>
          </div>
          {value.accounts.map((account) => (
            <div className="report-table-row" key={account.account_id}>
              <span>
                <small>{account.code}</small>
                {account.name}
              </span>
              <span>{formatMoney(account.debit_balance, currency, digits)}</span>
              <span>{formatMoney(account.credit_balance, currency, digits)}</span>
            </div>
          ))}
          <div className="report-table-row report-total">
            <span>Total</span>
            <span>{formatMoney(value.total_debits, currency, digits)}</span>
            <span>{formatMoney(value.total_credits, currency, digits)}</span>
          </div>
        </div>
      </ReportSurface>
    );
  }
  if (result.kind === "cash") {
    const value = result.value;
    if (value === null) return null;
    return (
      <ReportSurface
        title="Cash movements"
        subtitle={`${formatFinancialDate(value.starts_on)} — ${formatFinancialDate(value.ends_on)}`}
        status={<Badge tone="neutral">Unclassified</Badge>}
      >
        <Notice>
          These are ledger movements for the accounts you selected. Operating, investing, and
          financing classifications are intentionally deferred.
        </Notice>
        <dl className="metric-grid">
          <div>
            <dt>Inflows</dt>
            <dd>{formatMoney(value.total_inflows, currency, digits)}</dd>
          </div>
          <div>
            <dt>Outflows</dt>
            <dd>{formatMoney(value.total_outflows, currency, digits)}</dd>
          </div>
          <div>
            <dt>Net change</dt>
            <dd>{formatMoney(value.net_change, currency, digits)}</dd>
          </div>
        </dl>
        <LedgerRows lines={value.movements} currency={currency} digits={digits} />
      </ReportSurface>
    );
  }
  return (
    <ReportSurface title="General ledger" subtitle={`${result.value.total} posted lines`}>
      <LedgerRows lines={result.value.items} currency={currency} digits={digits} />
    </ReportSurface>
  );
}

function ReportSurface({
  title,
  subtitle,
  status,
  children,
}: {
  title: string;
  subtitle: string;
  status?: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <section className="surface report-surface">
      <header>
        <div>
          <p className="eyebrow">Ledger report</p>
          <h2>{title}</h2>
          <p>{subtitle}</p>
        </div>
        {status}
      </header>
      {children}
    </section>
  );
}

function LedgerRows({
  lines,
  currency,
  digits,
}: {
  lines: LedgerLine[];
  currency: string;
  digits: number;
}) {
  if (lines.length === 0)
    return (
      <EmptyState
        icon="reports"
        title="No report activity"
        description="No posted ledger lines match this report range."
      />
    );
  return (
    <div className="data-list">
      {lines.map((line) => (
        <a className="data-row linked-row" href={`/money/${line.entry_id}`} key={line.line_id}>
          <span>
            <small>
              {formatFinancialDate(line.entry_date)} · {line.code}
            </small>
            <strong>{line.description}</strong>
            <em>{line.account_name}</em>
          </span>
          <span className="aligned-numbers">
            <small>{line.debit ? "Debit" : "Credit"}</small>
            <strong>{formatMoney(line.debit || line.credit, currency, digits)}</strong>
          </span>
        </a>
      ))}
    </div>
  );
}
