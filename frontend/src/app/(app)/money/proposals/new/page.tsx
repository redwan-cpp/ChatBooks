"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useCallback } from "react";

import { ButtonLink, ErrorState, LoadingState, PageHeader } from "@/components/ui";
import { useFinancialSpace } from "@/features/context/financial-space-provider";
import { ProposalForm, type ProposalFormValue } from "@/features/money/proposal-form";
import { useResource } from "@/hooks/use-resource";
import { api } from "@/lib/api/client";

export default function NewProposalPage() {
  const { organization } = useFinancialSpace();
  const router = useRouter();
  const searchParams = useSearchParams();
  const load = useCallback(
    () => Promise.all([api.accounts(organization!.id), api.projects(organization!.id, 0, 100)]),
    [organization],
  );
  const resource = useResource(load);
  async function create(value: ProposalFormValue) {
    const proposal = await api.createProposal(organization!.id, value);
    router.push(`/money/proposals/${proposal.id}`);
  }
  return (
    <div className="page">
      <PageHeader
        eyebrow="Structured accounting action"
        title="Record a financial event"
        description="Create a reviewable proposal. Nothing posts from this form."
        action={
          <ButtonLink href="/money" variant="secondary">
            Cancel
          </ButtonLink>
        }
      />
      {resource.loading ? (
        <LoadingState label="Loading accounts and projects" />
      ) : resource.error || !resource.data ? (
        <ErrorState
          error={resource.error ?? new Error("Setup data is unavailable.")}
          onRetry={resource.reload}
        />
      ) : (
        <ProposalForm
          accounts={resource.data[0].items}
          projects={resource.data[1].items}
          minorUnitDigits={organization!.minor_unit_digits}
          initialProjectId={searchParams.get("project") ?? ""}
          onSubmit={create}
        />
      )}
    </div>
  );
}
