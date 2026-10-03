"use client";

import { useCallback, useState } from "react";

import { ButtonLink, ErrorState, LoadingState, PageHeader } from "@/components/ui";
import { useFinancialSpace } from "@/features/context/financial-space-provider";
import { ProjectList } from "@/features/projects/project-list";
import { useResource } from "@/hooks/use-resource";
import { api } from "@/lib/api/client";
import { allows } from "@/lib/permissions";

const PAGE_SIZE = 12;

export default function ProjectsPage() {
  const { organization } = useFinancialSpace();
  const [offset, setOffset] = useState(0);
  const organizationId = organization?.id ?? "";
  const load = useCallback(
    () => api.projects(organizationId, offset, PAGE_SIZE),
    [organizationId, offset],
  );
  const resource = useResource(load);
  if (!organization) return null;

  return (
    <div className="page">
      <PageHeader
        eyebrow="Business work"
        title="Projects"
        description="Keep client context and plans together, then view financial activity derived from the ledger."
        action={
          allows(organization.role, "manage_project") ? (
            <ButtonLink href="/projects/new">Create project</ButtonLink>
          ) : undefined
        }
      />
      {resource.loading ? (
        <LoadingState label="Loading projects" />
      ) : resource.error ? (
        <ErrorState error={resource.error} onRetry={resource.reload} />
      ) : resource.data ? (
        <>
          <ProjectList
            projects={resource.data.items}
            currency={organization.currency}
            minorUnitDigits={organization.minor_unit_digits}
          />
          {resource.data.total > PAGE_SIZE && (
            <div className="pagination">
              <button
                disabled={offset === 0}
                onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
              >
                Previous
              </button>
              <span>
                {offset + 1}–{Math.min(offset + PAGE_SIZE, resource.data.total)} of{" "}
                {resource.data.total}
              </span>
              <button
                disabled={offset + PAGE_SIZE >= resource.data.total}
                onClick={() => setOffset(offset + PAGE_SIZE)}
              >
                Next
              </button>
            </div>
          )}
        </>
      ) : null}
    </div>
  );
}
