import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { AccountDetail } from "@/features/money/account-detail";
import { MoneyWorkspace } from "@/features/money/money-views";
import { ProposalWorkflow } from "@/features/money/proposal-workflow";
import type {
  Account,
  IncomeStatement,
  JournalEntrySummary,
  Organization,
  Proposal,
  TrialBalance,
} from "@/lib/api/types";

const apiMocks = vi.hoisted(() => ({
  accounts: vi.fn(),
  createAccount: vi.fn(),
  updateAccount: vi.fn(),
  trialBalance: vi.fn(),
  incomeStatement: vi.fn(),
  journalEntries: vi.fn(),
  projects: vi.fn(),
}));

vi.mock("@/lib/api/client", () => ({ api: apiMocks }));

const organization: Organization = {
  id: "org-1",
  name: "North Studio",
  currency: "BDT",
  minor_unit_digits: 2,
  role: "ACCOUNTANT",
};

const accounts: Account[] = [
  {
    id: "cash",
    organization_id: organization.id,
    code: "1000",
    name: "Operating cash",
    account_type: "asset",
    active: true,
  },
  {
    id: "revenue",
    organization_id: organization.id,
    code: "4000",
    name: "Service revenue",
    account_type: "revenue",
    active: true,
  },
  {
    id: "expense",
    organization_id: organization.id,
    code: "5100",
    name: "Project supplies",
    account_type: "expense",
    active: false,
  },
];

const trialBalance: TrialBalance = {
  currency: "BDT",
  minor_unit_digits: 2,
  as_of: "2026-09-30",
  project_id: null,
  accounts: [
    {
      account_id: "cash",
      code: "1000",
      name: "Operating cash",
      account_type: "asset",
      debits: 500000,
      credits: 125000,
      net_debit: 375000,
      debit_balance: 375000,
      credit_balance: 0,
    },
    {
      account_id: "revenue",
      code: "4000",
      name: "Service revenue",
      account_type: "revenue",
      debits: 0,
      credits: 500000,
      net_debit: -500000,
      debit_balance: 0,
      credit_balance: 500000,
    },
    {
      account_id: "expense",
      code: "5100",
      name: "Project supplies",
      account_type: "expense",
      debits: 125000,
      credits: 0,
      net_debit: 125000,
      debit_balance: 125000,
      credit_balance: 0,
    },
  ],
  total_debits: 625000,
  total_credits: 625000,
  balanced: true,
};

const incomeStatement: IncomeStatement = {
  currency: "BDT",
  minor_unit_digits: 2,
  starts_on: "2026-09-01",
  ends_on: "2026-09-30",
  revenue: 500000,
  expenses: 125000,
  net_income: 375000,
};

const entry: JournalEntrySummary = {
  id: "entry-1",
  organization_id: organization.id,
  transaction_id: "proposal-1",
  confirmation_id: "confirmation-1",
  period_id: "period-1",
  entry_date: "2026-09-20",
  description: "Project supplies purchase",
  reverses_entry_id: null,
  state: "posted",
  debit_total: 125000,
  credit_total: 125000,
  line_count: 2,
  project_ids: [],
};

beforeEach(() => {
  vi.clearAllMocks();
  apiMocks.trialBalance.mockResolvedValue(trialBalance);
  apiMocks.incomeStatement.mockResolvedValue(incomeStatement);
  apiMocks.journalEntries.mockResolvedValue({ items: [entry], total: 1, offset: 0, limit: 5 });
  apiMocks.projects.mockResolvedValue({ items: [], total: 0, offset: 0, limit: 100 });
  apiMocks.accounts.mockResolvedValue({ items: accounts, total: 3, offset: 0, limit: 12 });
  apiMocks.createAccount.mockResolvedValue(accounts[0]);
  apiMocks.updateAccount.mockResolvedValue(accounts[0]);
});

describe("Chatbooks BUSINESS Money workspace", () => {
  it("renders API-backed overview totals, balances, and recent activity without duplicate loads", async () => {
    render(<MoneyWorkspace organization={organization} />);

    expect(await screen.findByText("How the business is moving")).toBeInTheDocument();
    expect(screen.getAllByText("৳5,000.00")).toHaveLength(2);
    expect(screen.getAllByText("৳1,250.00")).toHaveLength(3);
    expect(screen.getByText("৳3,750.00")).toBeInTheDocument();
    expect(screen.getByText("Project supplies purchase")).toBeInTheDocument();
    expect(apiMocks.trialBalance).toHaveBeenCalledOnce();
    expect(apiMocks.incomeStatement).toHaveBeenCalledOnce();
    expect(apiMocks.accounts).toHaveBeenCalledOnce();
    expect(apiMocks.journalEntries).toHaveBeenCalledOnce();
  });

  it("presents income and spending aggregates with honest detail boundaries", async () => {
    const user = userEvent.setup();
    render(<MoneyWorkspace organization={organization} />);
    await screen.findByText("How the business is moving");

    await user.click(screen.getByRole("tab", { name: "Income" }));
    expect(screen.getByText("Total revenue")).toBeInTheDocument();
    expect(screen.getByText("৳5,000.00")).toBeInTheDocument();
    expect(screen.getByText(/does not provide product categories/i)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Open activity" })).toHaveAttribute(
      "href",
      "/activity",
    );

    await user.click(screen.getByRole("tab", { name: "Spending" }));
    expect(screen.getByText("Total expenses")).toBeInTheDocument();
    expect(screen.getByText("৳1,250.00")).toBeInTheDocument();
    expect(
      screen.getByText(/Transfers are not included as spending by the UI/i),
    ).toBeInTheDocument();
    expect(apiMocks.trialBalance).toHaveBeenCalledOnce();
    expect(apiMocks.incomeStatement).toHaveBeenCalledOnce();
  });

  it("applies a valid financial date range to the reporting API", async () => {
    const user = userEvent.setup();
    render(<MoneyWorkspace organization={organization} />);
    await screen.findByText("How the business is moving");

    fireEvent.change(screen.getByLabelText("From"), { target: { value: "2026-08-01" } });
    fireEvent.change(screen.getByLabelText("To"), { target: { value: "2026-08-31" } });
    await user.click(screen.getByRole("button", { name: "Apply range" }));

    await waitFor(() =>
      expect(apiMocks.incomeStatement).toHaveBeenLastCalledWith(
        organization.id,
        "2026-08-01",
        "2026-08-31",
      ),
    );
    expect(apiMocks.trialBalance).toHaveBeenLastCalledWith(organization.id, {
      as_of: "2026-08-31",
    });
  });

  it("filters the loaded account page and paginates through the API", async () => {
    apiMocks.accounts.mockImplementation((_organizationId: string, offset: number) =>
      offset === 12
        ? Promise.resolve({
            items: [{ ...accounts[0], id: "reserve", code: "1010", name: "Reserve cash" }],
            total: 13,
            offset: 12,
            limit: 12,
          })
        : Promise.resolve({ items: accounts, total: 13, offset: 0, limit: 12 }),
    );
    const user = userEvent.setup();
    render(<MoneyWorkspace organization={organization} />);
    await user.click(screen.getByRole("tab", { name: "Accounts" }));

    expect(await screen.findByRole("link", { name: "View Operating cash" })).toHaveAttribute(
      "href",
      "/money/accounts/cash",
    );
    expect(screen.getByText("Inactive", { selector: ".badge" })).toBeInTheDocument();
    expect(screen.getByText(/Filters apply to the loaded page/i)).toBeInTheDocument();

    await user.type(screen.getByRole("searchbox", { name: "Find on this page" }), "operating");
    expect(screen.getByText("Operating cash")).toBeInTheDocument();
    expect(screen.queryByText("Service revenue")).not.toBeInTheDocument();
    await user.clear(screen.getByRole("searchbox", { name: "Find on this page" }));

    await user.click(screen.getByRole("button", { name: "Next" }));
    expect(await screen.findByText("Reserve cash")).toBeInTheDocument();
    expect(apiMocks.accounts).toHaveBeenLastCalledWith(organization.id, 12, 12);
    expect(screen.getByText("Showing 13–13 of 13")).toBeInTheDocument();
  });

  it("keeps transfers in a truthful deferred state", async () => {
    const user = userEvent.setup();
    render(<MoneyWorkspace organization={organization} />);
    await user.click(screen.getByRole("tab", { name: "Transfers" }));
    expect(screen.getByText("Guided transfers are not enabled")).toBeInTheDocument();
    expect(screen.getByText(/has no dedicated transfer workflow/i)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /create transfer/i })).not.toBeInTheDocument();
  });

  it("provides loading, error, and empty states", async () => {
    apiMocks.trialBalance.mockImplementation(() => new Promise(() => undefined));
    const loading = render(<MoneyWorkspace organization={organization} />);
    expect(screen.getByRole("status", { name: "Loading Money overview" })).toBeInTheDocument();
    loading.unmount();

    apiMocks.trialBalance.mockRejectedValue(new Error("Reports are temporarily unavailable"));
    const failed = render(<MoneyWorkspace organization={organization} />);
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Reports are temporarily unavailable",
    );
    failed.unmount();

    apiMocks.trialBalance.mockResolvedValue({ ...trialBalance, accounts: [] });
    apiMocks.journalEntries.mockResolvedValue({ items: [], total: 0, offset: 0, limit: 5 });
    render(<MoneyWorkspace organization={organization} />);
    expect(await screen.findByText("No money accounts yet")).toBeInTheDocument();
    expect(screen.getByText("No posted activity yet")).toBeInTheDocument();
  });
});

describe("account detail and proposal disclosure", () => {
  it("shows the exact account report fields through progressive disclosure", async () => {
    const user = userEvent.setup();
    render(
      <AccountDetail
        account={accounts[0]!}
        balance={trialBalance.accounts[0]!}
        report={trialBalance}
        organization={organization}
      />,
    );
    expect(screen.getAllByText("৳3,750.00")).toHaveLength(2);
    expect(screen.getByText(/account-specific activity filter/i)).toBeInTheDocument();
    const detail = screen.getByText("Accounting detail").closest("details");
    expect(detail).not.toBeNull();
    expect(detail).not.toHaveAttribute("open");
    await user.click(within(detail as HTMLElement).getByText("Accounting detail"));
    expect(detail).toHaveAttribute("open");
    expect(within(detail as HTMLElement).getByText("৳5,000.00")).toBeInTheDocument();
    expect(within(detail as HTMLElement).getByText("৳1,250.00")).toBeInTheDocument();
    expect(document.body).not.toHaveTextContent(/ledger[_ -]?book/i);
  });

  it("explains the five explicit proposal stages", () => {
    const proposal: Proposal = {
      id: "proposal-1",
      organization_id: organization.id,
      entry_date: "2026-09-30",
      description: "Project supplies purchase",
      document_id: null,
      reverses_entry_id: null,
      version: 1,
      state: "proposed",
      lines: [
        {
          position: 1,
          account_id: "expense",
          code: "5100",
          name: "Project supplies",
          debit: 125000,
          credit: 0,
          project_id: null,
        },
        {
          position: 2,
          account_id: "cash",
          code: "1000",
          name: "Operating cash",
          debit: 0,
          credit: 125000,
          project_id: null,
        },
      ],
      posted_entry_id: null,
      status: "proposed",
      lifecycle_state: "PROPOSED",
      currency: "BDT",
      minor_unit_digits: 2,
    };
    render(
      <ProposalWorkflow
        proposal={proposal}
        organization={organization}
        onValidate={vi.fn()}
        onConfirm={vi.fn()}
        onPost={vi.fn()}
      />,
    );
    const progress = screen.getByRole("list", { name: "Proposal progress" });
    expect(
      within(progress)
        .getAllByRole("listitem")
        .map((item) => item.textContent),
    ).toEqual(["✓Draft", "2Validate", "3Review", "4Confirm", "5Post"]);
    expect(within(progress).getByText("Validate").closest("li")).toHaveAttribute(
      "aria-current",
      "step",
    );
  });
});
