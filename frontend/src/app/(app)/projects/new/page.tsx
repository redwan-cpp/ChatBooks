"use client";

import { useRouter } from "next/navigation";

import { Notice, PageHeader } from "@/components/ui";
import { useFinancialSpace } from "@/features/context/financial-space-provider";
import { ProjectForm } from "@/features/projects/project-form";
import { api } from "@/lib/api/client";
import { allows } from "@/lib/permissions";

export default function NewProjectPage() {
  const router = useRouter();
  const { organization } = useFinancialSpace();
  if (!organization) return null;
  if (!allows(organization.role, "manage_project")) {
    return (
      <div className="page">
        <PageHeader title="Create project" />
        <Notice tone="warning">Your role does not allow project changes.</Notice>
      </div>
    );
  }
  return (
    <div className="page narrow-page">
      <PageHeader
        eyebrow="New project"
        title="Create a project"
        description="Add context and planning values. Actual financial activity remains derived from posted ledger entries."
      />
      <ProjectForm
        minorUnitDigits={organization.minor_unit_digits}
        onSubmit={async (value) => {
          const created = await api.createProject(organization.id, value);
          router.push(`/projects/${created.id}`);
        }}
      />
    </div>
  );
}
