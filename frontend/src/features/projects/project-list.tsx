import Link from "next/link";

import { Badge, EmptyState } from "@/components/ui";
import type { Project } from "@/lib/api/types";
import { formatFinancialDate, formatMoney } from "@/lib/money";

export function ProjectList({
  projects,
  currency,
  minorUnitDigits,
}: {
  projects: Project[];
  currency: string;
  minorUnitDigits: number;
}) {
  if (projects.length === 0) {
    return (
      <EmptyState
        icon="projects"
        title="No projects yet"
        description="Create a project to organize context, planning values, and project-tagged ledger activity."
      />
    );
  }
  return (
    <div className="project-grid">
      {projects.map((project) => (
        <Link className="project-card" href={`/projects/${project.id}`} key={project.id}>
          <div className="project-card-top">
            <Badge tone={project.status === "active" ? "success" : "neutral"}>
              {project.status}
            </Badge>
            <span aria-hidden="true">↗</span>
          </div>
          <div>
            <h2>{project.name}</h2>
            <p>{project.client ?? "No client recorded"}</p>
          </div>
          <dl className="project-plan-row">
            <div>
              <dt>Budget plan</dt>
              <dd>
                {project.budget === null
                  ? "Not set"
                  : formatMoney(project.budget, currency, minorUnitDigits)}
              </dd>
            </div>
            <div>
              <dt>Expected revenue</dt>
              <dd>
                {project.expected_revenue === null
                  ? "Not set"
                  : formatMoney(project.expected_revenue, currency, minorUnitDigits)}
              </dd>
            </div>
          </dl>
          <p className="project-dates">
            {project.starts_on ? formatFinancialDate(project.starts_on) : "No start date"}
            {project.ends_on ? ` — ${formatFinancialDate(project.ends_on)}` : ""}
          </p>
        </Link>
      ))}
    </div>
  );
}
