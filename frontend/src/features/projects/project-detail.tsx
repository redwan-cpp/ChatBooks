import Link from "next/link";

import { Badge, ButtonLink, EmptyState, Notice } from "@/components/ui";
import type { Organization, Page, Project, LedgerLine, TrialBalance } from "@/lib/api/types";
import { formatFinancialDate, formatMoney } from "@/lib/money";
import { allows } from "@/lib/permissions";

export function ProjectDetail({
  project,
  organization,
  activity,
  trialBalance,
}: {
  project: Project;
  organization: Organization;
  activity: Page<LedgerLine>;
  trialBalance: TrialBalance;
}) {
  return (
    <div className="section-stack">
      <section className="project-hero surface">
        <div>
          <div className="project-title-line">
            <Badge tone={project.status === "active" ? "success" : "neutral"}>
              {project.status}
            </Badge>
            <span>{project.client ?? "No client recorded"}</span>
          </div>
          <h2>{project.name}</h2>
          <p>{project.description || "No project context has been added yet."}</p>
        </div>
        {allows(organization.role, "manage_project") && (
          <ButtonLink href={`/projects/${project.id}/edit`} variant="secondary">
            Edit project
          </ButtonLink>
        )}
      </section>

      <section className="surface">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Planning</p>
            <h2>Project expectations</h2>
            <p>
              These are editable planning values. They are separate from posted financial activity.
            </p>
          </div>
        </div>
        <dl className="metric-grid">
          <div>
            <dt>Budget plan</dt>
            <dd>
              {project.budget === null
                ? "Not set"
                : formatMoney(
                    project.budget,
                    organization.currency,
                    organization.minor_unit_digits,
                  )}
            </dd>
          </div>
          <div>
            <dt>Expected revenue</dt>
            <dd>
              {project.expected_revenue === null
                ? "Not set"
                : formatMoney(
                    project.expected_revenue,
                    organization.currency,
                    organization.minor_unit_digits,
                  )}
            </dd>
          </div>
          <div>
            <dt>Starts</dt>
            <dd>{project.starts_on ? formatFinancialDate(project.starts_on) : "Not set"}</dd>
          </div>
          <div>
            <dt>Ends</dt>
            <dd>{project.ends_on ? formatFinancialDate(project.ends_on) : "Not set"}</dd>
          </div>
        </dl>
        <Notice>
          Budget remaining and collected revenue are not shown because the current accounting model
          does not yet define those classifications.
        </Notice>
      </section>

      <section className="surface">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Ledger derived</p>
            <h2>Account balances for this project</h2>
            <p>Every value below comes from project-tagged posted journal lines.</p>
          </div>
        </div>
        {trialBalance.accounts.length === 0 ? (
          <EmptyState
            icon="money"
            title="No posted project balances"
            description="Post a proposal with this project assigned to its journal lines to see financial activity here."
          />
        ) : (
          <div className="data-list">
            {trialBalance.accounts.map((account) => (
              <div className="data-row" key={account.account_id}>
                <span>
                  <small>
                    {account.code} · {account.account_type}
                  </small>
                  <strong>{account.name}</strong>
                </span>
                <span className="aligned-numbers">
                  <small>Net balance</small>
                  <strong>
                    {formatMoney(
                      account.net_debit,
                      organization.currency,
                      organization.minor_unit_digits,
                    )}
                  </strong>
                </span>
              </div>
            ))}
          </div>
        )}
      </section>

      <section className="surface">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Activity</p>
            <h2>Posted project lines</h2>
            <p>General-ledger detail scoped to this project.</p>
          </div>
          {allows(organization.role, "create_proposal") && (
            <ButtonLink href={`/money/proposals/new?project=${project.id}`} variant="secondary">
              New proposal
            </ButtonLink>
          )}
        </div>
        {activity.items.length === 0 ? (
          <EmptyState
            icon="activity"
            title="No project activity"
            description="There are no posted ledger lines associated with this project."
          />
        ) : (
          <div className="data-list">
            {activity.items.map((line) => (
              <Link
                className="data-row linked-row"
                href={`/money/${line.entry_id}`}
                key={line.line_id}
              >
                <span>
                  <small>
                    {formatFinancialDate(line.entry_date)} · {line.code}
                  </small>
                  <strong>{line.description}</strong>
                  <em>{line.account_name}</em>
                </span>
                <span className="aligned-numbers">
                  <small>{line.debit ? "Debit" : "Credit"}</small>
                  <strong>
                    {formatMoney(
                      line.debit || line.credit,
                      organization.currency,
                      organization.minor_unit_digits,
                    )}
                  </strong>
                </span>
              </Link>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
