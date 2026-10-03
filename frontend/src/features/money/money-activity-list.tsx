import Link from "next/link";

import { Badge, EmptyState } from "@/components/ui";
import type { JournalEntrySummary, Project } from "@/lib/api/types";
import { formatFinancialDate, formatMoney } from "@/lib/money";

export function MoneyActivityList({
  entries,
  projects,
  currency,
  minorUnitDigits,
}: {
  entries: JournalEntrySummary[];
  projects: Project[];
  currency: string;
  minorUnitDigits: number;
}) {
  const projectNames = new Map(projects.map((project) => [project.id, project.name]));
  if (entries.length === 0) {
    return (
      <EmptyState
        icon="money"
        title="No posted activity yet"
        description="Validated and confirmed proposals will appear here after they are posted."
      />
    );
  }
  return (
    <div className="activity-list">
      {entries.map((entry) => (
        <Link href={`/money/${entry.id}`} key={entry.id} className="activity-row">
          <span
            className={`activity-direction ${entry.reverses_entry_id ? "reversal" : "posted"}`}
            aria-hidden="true"
          />
          <span className="activity-copy">
            <strong>{entry.description}</strong>
            <small>
              {entry.project_ids.length > 0
                ? entry.project_ids.map((id) => projectNames.get(id) ?? "Project").join(", ")
                : "Business activity"}
              {" · "}
              {formatFinancialDate(entry.entry_date)}
            </small>
          </span>
          <span className="activity-meta">
            <strong>{formatMoney(entry.debit_total, currency, minorUnitDigits)}</strong>
            <Badge tone={entry.reverses_entry_id ? "warning" : "success"}>
              {entry.reverses_entry_id ? "Reversal" : "Posted"}
            </Badge>
          </span>
        </Link>
      ))}
    </div>
  );
}
