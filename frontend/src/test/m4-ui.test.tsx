import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { EmptyState, ErrorState, LoadingState } from "@/components/ui";
import { ActivityList } from "@/features/activity/activity-list";
import { AuthProvider } from "@/features/auth/auth-provider";
import { ProtectedRoute } from "@/features/auth/protected-route";
import { ContextSwitcher } from "@/features/context/context-switcher";
import { FinancialSpaceProvider } from "@/features/context/financial-space-provider";
import { PersonalDeferred } from "@/features/context/personal-deferred";
import { MoneyActivityList } from "@/features/money/money-activity-list";
import { ProposalWorkflow } from "@/features/money/proposal-workflow";
import { ProjectDetail } from "@/features/projects/project-detail";
import { ProjectList } from "@/features/projects/project-list";
import { ReportResult } from "@/features/reports/reports-view";
import type {
  Confirmation,
  JournalEntrySummary,
  Organization,
  Project,
  Proposal,
  Validation,
} from "@/lib/api/types";

const apiMocks = vi.hoisted(() => ({
  me: vi.fn(),
  organizations: vi.fn(),
  logout: vi.fn(),
  login: vi.fn(),
  register: vi.fn(),
}));
const navigationMocks = vi.hoisted(() => ({ replace: vi.fn(), push: vi.fn() }));

vi.mock("@/lib/api/client", () => ({
  api: apiMocks,
  ApiError: class ApiError extends Error {
    constructor(
      readonly code: string,
      message: string,
      readonly status: number,
    ) {
      super(message);
    }
  },
}));

vi.mock("next/navigation", () => ({
  useRouter: () => navigationMocks,
  usePathname: () => "/money",
  useSearchParams: () => new URLSearchParams(),
  useParams: () => ({}),
}));

const organization: Organization = {
  id: "org-1",
  name: "North Studio",
  currency: "BDT",
  minor_unit_digits: 2,
  role: "ACCOUNTANT",
};
const project: Project = {
  id: "project-1",
  organization_id: organization.id,
  name: "Client launch",
  description: "Launch work",
  client: "Client One",
  expected_revenue: 500000,
  budget: 300000,
  starts_on: "2026-09-01",
  ends_on: "2026-10-31",
  status: "active",
};
const entry: JournalEntrySummary = {
  id: "entry-1",
  organization_id: organization.id,
  transaction_id: "proposal-1",
  confirmation_id: "confirmation-1",
  period_id: "period-1",
  entry_date: "2026-09-20",
  description: "Project materials",
  reverses_entry_id: null,
  state: "posted",
  debit_total: 125000,
  credit_total: 125000,
  line_count: 2,
  project_ids: [project.id],
};

beforeEach(() => {
  vi.clearAllMocks();
  apiMocks.me.mockResolvedValue({ id: "user-1", name: "Sam", username: "sam" });
  apiMocks.organizations.mockResolvedValue([organization]);
  apiMocks.logout.mockResolvedValue(undefined);
});

describe("authentication and financial context", () => {
  it("redirects an unauthenticated protected route", async () => {
    apiMocks.me.mockRejectedValue(new Error("Not authenticated"));
    render(
      <AuthProvider>
        <ProtectedRoute>
          <p>Private money</p>
        </ProtectedRoute>
      </AuthProvider>,
    );
    expect(screen.getByLabelText("Checking your session")).toBeInTheDocument();
    await waitFor(() =>
      expect(navigationMocks.replace).toHaveBeenCalledWith("/login?next=%2Fmoney"),
    );
    expect(screen.queryByText("Private money")).not.toBeInTheDocument();
  });

  it("accepts an authenticated session and switches to the honest personal placeholder", async () => {
    const user = userEvent.setup();
    render(
      <AuthProvider>
        <ProtectedRoute>
          <FinancialSpaceProvider>
            <ContextSwitcher />
          </FinancialSpaceProvider>
        </ProtectedRoute>
      </AuthProvider>,
    );
    expect(await screen.findByText("North Studio")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /business space/i }));
    await user.click(screen.getByRole("menuitemradio", { name: /personal/i }));
    expect(screen.getByText("Personal")).toBeInTheDocument();
    expect(window.localStorage.getItem("chatbook_financial_space")).toBe("personal");
  });

  it("states clearly that personal data is deferred", () => {
    render(<PersonalDeferred />);
    expect(screen.getByText("Personal finance is coming later")).toBeInTheDocument();
    expect(screen.getByText(/no fabricated balances/i)).toBeInTheDocument();
  });
});

describe("business financial views", () => {
  it("renders project plans separately from ledger-derived balances", () => {
    render(
      <ProjectDetail
        project={project}
        organization={organization}
        activity={{ items: [], total: 0, offset: 0, limit: 50 }}
        trialBalance={{
          currency: "BDT",
          minor_unit_digits: 2,
          as_of: null,
          project_id: project.id,
          accounts: [
            {
              account_id: "account-1",
              code: "5100",
              name: "Materials",
              account_type: "expense",
              debits: 125000,
              credits: 0,
              net_debit: 125000,
              debit_balance: 125000,
              credit_balance: 0,
            },
          ],
          total_debits: 125000,
          total_credits: 125000,
          balanced: true,
        }}
      />,
    );
    expect(screen.getByText("Planning")).toBeInTheDocument();
    expect(screen.getByText("Account balances for this project")).toBeInTheDocument();
    expect(screen.getByText(/does not yet define those classifications/i)).toBeInTheDocument();
    expect(screen.getByText("৳1,250.00")).toBeInTheDocument();
  });

  it("renders project list and an explicit empty state", () => {
    const { rerender } = render(
      <ProjectList projects={[project]} currency="BDT" minorUnitDigits={2} />,
    );
    expect(screen.getByRole("link", { name: /client launch/i })).toHaveAttribute(
      "href",
      "/projects/project-1",
    );
    rerender(<ProjectList projects={[]} currency="BDT" minorUnitDigits={2} />);
    expect(screen.getByText("No projects yet")).toBeInTheDocument();
  });

  it("renders posted transaction amounts returned by the accounting engine", () => {
    render(
      <MoneyActivityList
        entries={[entry]}
        projects={[project]}
        currency="BDT"
        minorUnitDigits={2}
      />,
    );
    expect(screen.getByText("Project materials")).toBeInTheDocument();
    expect(screen.getByText("৳1,250.00")).toBeInTheDocument();
    expect(screen.getByText(/Client launch/)).toBeInTheDocument();
  });

  it("renders reconciled report values and audit provenance", () => {
    const { rerender } = render(
      <ReportResult
        currency="BDT"
        digits={2}
        result={{
          kind: "trial",
          value: {
            currency: "BDT",
            minor_unit_digits: 2,
            as_of: "2026-09-25",
            project_id: null,
            accounts: [
              {
                account_id: "cash",
                code: "1000",
                name: "Cash",
                account_type: "asset",
                debits: 200000,
                credits: 0,
                net_debit: 200000,
                debit_balance: 200000,
                credit_balance: 0,
              },
            ],
            total_debits: 200000,
            total_credits: 200000,
            balanced: true,
          },
        }}
      />,
    );
    expect(screen.getByText("Balanced")).toBeInTheDocument();
    expect(screen.getAllByText("৳2,000.00")).toHaveLength(3);
    rerender(
      <ActivityList
        currentUserId="user-1"
        events={[
          {
            sequence: 14,
            organization_id: organization.id,
            actor_id: "user-1",
            occurred_at: "2026-09-25T10:00:00Z",
            event_type: "JOURNAL_ENTRY_POSTED",
            entity_type: "journal_entry",
            entity_id: entry.id,
            previous_state: null,
            new_state: { state: "posted" },
            metadata: { operation: "post" },
          },
        ]}
      />,
    );
    expect(screen.getByText("Journal Entry Posted")).toBeInTheDocument();
    expect(screen.getByText(/You ·/)).toBeInTheDocument();
  });
});

describe("proposal safety and interface states", () => {
  const proposal: Proposal = {
    id: "proposal-1",
    organization_id: organization.id,
    entry_date: "2026-09-25",
    description: "Materials purchase",
    document_id: null,
    reverses_entry_id: null,
    version: 3,
    state: "proposed",
    lines: [
      {
        position: 1,
        account_id: "expense",
        code: "5100",
        name: "Materials",
        debit: 125000,
        credit: 0,
        project_id: project.id,
      },
      {
        position: 2,
        account_id: "cash",
        code: "1000",
        name: "Cash",
        debit: 0,
        credit: 125000,
        project_id: project.id,
      },
    ],
    posted_entry_id: null,
    status: "proposed",
    lifecycle_state: "PROPOSED",
    currency: "BDT",
    minor_unit_digits: 2,
  };
  const validation: Validation = {
    id: "validation-1",
    transaction_id: proposal.id,
    fingerprint: "fingerprint",
    debit_total: 125000,
    credit_total: 125000,
  };
  const confirmation: Confirmation = {
    id: "confirmation-1",
    validation_id: validation.id,
    actor_id: "user-1",
    proposal_id: proposal.id,
    proposal_version: proposal.version,
    confirmed_at: "2026-09-25T12:00:00Z",
    confirmation_request_id: "request-1",
  };

  it("hides validation from a viewer", () => {
    render(
      <ProposalWorkflow
        proposal={proposal}
        organization={{ ...organization, role: "VIEWER" }}
        onValidate={vi.fn()}
        onConfirm={vi.fn()}
        onPost={vi.fn()}
      />,
    );
    expect(screen.queryByRole("button", { name: "Validate proposal" })).not.toBeInTheDocument();
    expect(screen.getByText(/does not allow proposal validation/i)).toBeInTheDocument();
  });

  it("requires review of the exact version before confirmation", async () => {
    const user = userEvent.setup();
    const onValidate = vi.fn().mockResolvedValue(validation);
    const onConfirm = vi.fn().mockResolvedValue(confirmation);
    render(
      <ProposalWorkflow
        proposal={proposal}
        organization={organization}
        onValidate={onValidate}
        onConfirm={onConfirm}
        onPost={vi.fn()}
      />,
    );
    await user.click(screen.getByRole("button", { name: "Validate proposal" }));
    await user.click(await screen.findByRole("button", { name: "Review and confirm" }));
    const dialog = screen.getByRole("dialog");
    expect(within(dialog).getByText(/version 3/i)).toBeInTheDocument();
    const confirmButton = within(dialog).getByRole("button", { name: "Confirm proposal" });
    expect(confirmButton).toBeDisabled();
    await user.click(within(dialog).getByRole("checkbox"));
    await user.click(confirmButton);
    await waitFor(() => expect(onConfirm).toHaveBeenCalledWith(validation));
    expect(
      await screen.findByText(/Confirmation alone has not changed the ledger/i),
    ).toBeInTheDocument();
  });

  it("has accessible loading, error, and empty states", async () => {
    const retry = vi.fn();
    const { rerender } = render(<LoadingState label="Loading financial activity" />);
    expect(screen.getByRole("status", { name: "Loading financial activity" })).toBeInTheDocument();
    rerender(<ErrorState error={new Error("Service unavailable")} onRetry={retry} />);
    await userEvent.click(screen.getByRole("button", { name: /try again/i }));
    expect(retry).toHaveBeenCalledOnce();
    rerender(<EmptyState icon="money" title="Nothing here" description="No records match." />);
    expect(screen.getByText("Nothing here")).toBeInTheDocument();
  });
});
