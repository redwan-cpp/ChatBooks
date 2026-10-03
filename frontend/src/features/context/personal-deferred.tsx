import { ButtonLink, EmptyState, Notice } from "@/components/ui";

const copy = {
  Money:
    "Personal accounts, balances, income, spending, and transfers arrive after the Personal Finance Foundation.",
  Activity:
    "Personal financial activity requires the private personal finance backend planned for a later milestone.",
  Reports:
    "Personal reports will remain ledger-derived. They cannot be shown until the personal backend exists.",
  Settings:
    "Personal account and category settings are unavailable until the Personal Finance Foundation is implemented.",
  Projects: "Projects belong to business spaces and are not available in Personal context.",
} as const;

export function PersonalDeferred({ section }: { section?: keyof typeof copy }) {
  const title =
    section === "Projects" ? "Projects are business-only" : "Personal finance is coming later";
  return (
    <div className="deferred-view">
      <div className="deferred-orbit" aria-hidden="true">
        <span />
        <span />
      </div>
      <EmptyState
        icon="money"
        title={title}
        description={
          section
            ? copy[section]
            : "This space contains no fabricated balances, transactions, accounts, or reports."
        }
        action={
          section === "Projects" ? (
            <ButtonLink href="/chat" variant="secondary">
              Return to Chat
            </ButtonLink>
          ) : undefined
        }
      />
      <Notice>
        Personal financial operations are not enabled. Switch to a business to use capabilities
        backed by the current Chatbooks API.
      </Notice>
    </div>
  );
}
