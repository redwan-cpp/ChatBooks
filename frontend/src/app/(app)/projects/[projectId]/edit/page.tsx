"use client";

import { useParams, useRouter } from "next/navigation";
import { useCallback } from "react";

import { ErrorState, LoadingState, Notice, PageHeader } from "@/components/ui";
import { useFinancialSpace } from "@/features/context/financial-space-provider";
import { ProjectForm } from "@/features/projects/project-form";
import { useResource } from "@/hooks/use-resource";
import { api } from "@/lib/api/client";
import { allows } from "@/lib/permissions";

export default function EditProjectPage() {
  const params = useParams<{ projectId: string }>();
  const router = useRouter();
  const { organization } = useFinancialSpace();
  const organizationId = organization?.id ?? "";
  const projectId = params.projectId;
  const load = useCallback(
    () => api.project(organizationId, projectId),
    [organizationId, projectId],
  );
  const resource = useResource(load);
  if (!organization) return null;
  if (!allows(organization.role, "manage_project")) {
    return (
      <div className="page">
        <PageHeader title="Edit project" />
        <Notice tone="warning">Your role does not allow project changes.</Notice>
      </div>
    );
  }
  return (
    <div className="page narrow-page">
      <PageHeader
        eyebrow="Project settings"
        title="Edit project"
        description="Update context and planning values without altering posted financial history."
      />
      {resource.loading ? (
        <LoadingState label="Loading project" />
      ) : resource.error ? (
        <ErrorState error={resource.error} onRetry={resource.reload} />
      ) : resource.data ? (
        <ProjectForm
          project={resource.data}
          minorUnitDigits={organization.minor_unit_digits}
          onSubmit={async (value) => {
            await api.updateProject(organization.id, projectId, value);
            router.push(`/projects/${projectId}`);
          }}
        />
      ) : null}
    </div>
  );
}
