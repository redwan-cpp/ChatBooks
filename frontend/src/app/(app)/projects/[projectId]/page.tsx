"use client";

import { useParams } from "next/navigation";
import { useCallback } from "react";

import { ErrorState, LoadingState, PageHeader } from "@/components/ui";
import { useFinancialSpace } from "@/features/context/financial-space-provider";
import { ProjectDetail } from "@/features/projects/project-detail";
import { useResource } from "@/hooks/use-resource";
import { api } from "@/lib/api/client";

export default function ProjectDetailPage() {
  const params = useParams<{ projectId: string }>();
  const { organization } = useFinancialSpace();
  const organizationId = organization?.id ?? "";
  const projectId = params.projectId;
  const load = useCallback(async () => {
    const [project, activity, trialBalance] = await Promise.all([
      api.project(organizationId, projectId),
      api.generalLedger(organizationId, { project_id: projectId, limit: 50 }),
      api.trialBalance(organizationId, { project_id: projectId }),
    ]);
    return { project, activity, trialBalance };
  }, [organizationId, projectId]);
  const resource = useResource(load);
  if (!organization) return null;
  return (
    <div className="page">
      <PageHeader
        eyebrow="Project"
        title={resource.data?.project.name ?? "Project detail"}
        description="Plans and posted financial activity, kept visibly separate."
      />
      {resource.loading ? (
        <LoadingState label="Loading project" />
      ) : resource.error ? (
        <ErrorState error={resource.error} onRetry={resource.reload} />
      ) : resource.data ? (
        <ProjectDetail
          project={resource.data.project}
          organization={organization}
          activity={resource.data.activity}
          trialBalance={resource.data.trialBalance}
        />
      ) : null}
    </div>
  );
}
