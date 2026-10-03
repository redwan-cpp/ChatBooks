"use client";

import { useCallback, useMemo, useState } from "react";

import { Button, ErrorState, Field, LoadingState, PageHeader, Tabs } from "@/components/ui";
import { ActivityList } from "@/features/activity/activity-list";
import { useAuth } from "@/features/auth/auth-provider";
import { useFinancialSpace } from "@/features/context/financial-space-provider";
import { MoneyActivityList } from "@/features/money/money-activity-list";
import { useResource } from "@/hooks/use-resource";
import { api } from "@/lib/api/client";
import type { Organization, User } from "@/lib/api/types";
import { allows } from "@/lib/permissions";

const ACTIVITY_PAGE_SIZE = 20;
const AUDIT_PAGE_SIZE = 30;

type ActivityView = "money" | "audit";

export default function ActivityPage() {
  const { user } = useAuth();
  const { organization } = useFinancialSpace();
  const [view, setView] = useState<ActivityView>("money");
  if (!organization || !user) return null;
  const canAudit = allows(organization.role, "view_audit");
  const options: Array<{ id: ActivityView; label: string }> = canAudit
    ? [
        { id: "money", label: "Money activity" },
        { id: "audit", label: "Audit trail" },
      ]
    : [{ id: "money", label: "Money activity" }];
  return (
    <div className="page">
      <PageHeader
        eyebrow="Chronological history"
        title="Activity"
        description="Follow posted financial events first, then open immutable evidence when your role allows it."
      />
      <Tabs label="Activity views" value={view} options={options} onChange={setView} />
      <div className="tab-panel" role="tabpanel">
        {view === "audit" && canAudit ? (
          <AuditHistoryView organization={organization} user={user} />
        ) : (
          <FinancialActivityView organization={organization} />
        )}
      </div>
    </div>
  );
}

function FinancialActivityView({ organization }: { organization: Organization }) {
  const [offset, setOffset] = useState(0);
  const [search, setSearch] = useState("");
  const [projectId, setProjectId] = useState("");
  const load = useCallback(
    () =>
      Promise.all([
        api.journalEntries(organization.id, offset, ACTIVITY_PAGE_SIZE),
        api.projects(organization.id, 0, 100),
      ]),
    [offset, organization.id],
  );
  const resource = useResource(load);
  const entries = resource.data?.[0];
  const projects = resource.data?.[1].items ?? [];
  const filtered = useMemo(
    () =>
      (entries?.items ?? []).filter((entry) => {
        const matchesSearch = entry.description.toLowerCase().includes(search.toLowerCase());
        const matchesProject = !projectId || entry.project_ids.includes(projectId);
        return matchesSearch && matchesProject;
      }),
    [entries, projectId, search],
  );
  if (resource.loading) return <LoadingState label="Loading financial activity" />;
  if (resource.error) return <ErrorState error={resource.error} onRetry={resource.reload} />;
  return (
    <section className="section-stack">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Posted financial events</p>
          <h2>Money activity</h2>
          <p>Every amount and state comes from the accounting engine.</p>
        </div>
      </div>
      <div className="filter-row">
        <Field label="Search this page">
          <input
            type="search"
            placeholder="Description"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
          />
        </Field>
        <Field label="Project on this page">
          <select value={projectId} onChange={(event) => setProjectId(event.target.value)}>
            <option value="">All projects</option>
            {projects.map((project) => (
              <option key={project.id} value={project.id}>
                {project.name}
              </option>
            ))}
          </select>
        </Field>
      </div>
      <MoneyActivityList
        entries={filtered}
        projects={projects}
        currency={organization.currency}
        minorUnitDigits={organization.minor_unit_digits}
      />
      {entries && entries.total > entries.limit && (
        <div className="pagination">
          <Button
            variant="secondary"
            disabled={offset === 0}
            onClick={() => setOffset(Math.max(0, offset - entries.limit))}
          >
            Previous
          </Button>
          <span>
            {offset + 1}–{Math.min(offset + entries.limit, entries.total)} of {entries.total}
          </span>
          <Button
            variant="secondary"
            disabled={offset + entries.limit >= entries.total}
            onClick={() => setOffset(offset + entries.limit)}
          >
            Next
          </Button>
        </div>
      )}
    </section>
  );
}

function AuditHistoryView({ organization, user }: { organization: Organization; user: User }) {
  const [offset, setOffset] = useState(0);
  const [entityId, setEntityId] = useState("");
  const [appliedEntityId, setAppliedEntityId] = useState("");
  const load = useCallback(
    () => api.auditEvents(organization.id, offset, AUDIT_PAGE_SIZE, appliedEntityId || undefined),
    [appliedEntityId, offset, organization.id],
  );
  const resource = useResource(load);
  return (
    <section className="section-stack">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Advanced evidence</p>
          <h2>Audit trail</h2>
          <p>See who changed what and when. This record cannot be edited here.</p>
        </div>
      </div>
      <form
        className="surface filter-row"
        onSubmit={(event) => {
          event.preventDefault();
          setOffset(0);
          setAppliedEntityId(entityId.trim());
        }}
      >
        <Field label="Find an entity">
          <input
            placeholder="Exact entity ID"
            value={entityId}
            onChange={(event) => setEntityId(event.target.value)}
          />
        </Field>
        <Button type="submit" variant="secondary">
          Apply filter
        </Button>
        {appliedEntityId && (
          <Button
            type="button"
            variant="quiet"
            onClick={() => {
              setEntityId("");
              setAppliedEntityId("");
              setOffset(0);
            }}
          >
            Clear
          </Button>
        )}
      </form>
      {resource.loading ? (
        <LoadingState label="Loading audit activity" />
      ) : resource.error ? (
        <ErrorState error={resource.error} onRetry={resource.reload} />
      ) : resource.data ? (
        <>
          <ActivityList events={resource.data.items} currentUserId={user.id} />
          {resource.data.total > AUDIT_PAGE_SIZE && (
            <div className="pagination">
              <Button
                variant="secondary"
                disabled={offset === 0}
                onClick={() => setOffset(Math.max(0, offset - AUDIT_PAGE_SIZE))}
              >
                Previous
              </Button>
              <span>
                {offset + 1}–{Math.min(offset + AUDIT_PAGE_SIZE, resource.data.total)} of{" "}
                {resource.data.total}
              </span>
              <Button
                variant="secondary"
                disabled={offset + AUDIT_PAGE_SIZE >= resource.data.total}
                onClick={() => setOffset(offset + AUDIT_PAGE_SIZE)}
              >
                Next
              </Button>
            </div>
          )}
        </>
      ) : null}
    </section>
  );
}
