"use client";

import { useParams, useRouter } from "next/navigation";
import { useCallback } from "react";

import { ButtonLink, ErrorState, LoadingState, PageHeader } from "@/components/ui";
import { useFinancialSpace } from "@/features/context/financial-space-provider";
import { ProposalWorkflow } from "@/features/money/proposal-workflow";
import { useResource } from "@/hooks/use-resource";
import { api } from "@/lib/api/client";
import type { Confirmation, Validation } from "@/lib/api/types";

export default function ProposalPage() {
  const params = useParams<{ proposalId: string }>();
  const router = useRouter();
  const { organization } = useFinancialSpace();
  const load = useCallback(
    () => api.proposal(organization!.id, params.proposalId),
    [organization, params.proposalId],
  );
  const resource = useResource(load);
  if (resource.loading)
    return (
      <div className="page">
        <LoadingState label="Loading proposal" />
      </div>
    );
  if (resource.error || !resource.data)
    return (
      <div className="page">
        <ErrorState
          error={resource.error ?? new Error("Proposal not found.")}
          onRetry={resource.reload}
        />
      </div>
    );
  async function validate(): Promise<Validation> {
    return api.validateProposal(organization!.id, params.proposalId);
  }
  async function confirm(validation: Validation): Promise<Confirmation> {
    return api.confirmProposal(
      organization!.id,
      params.proposalId,
      validation.id,
      resource.data!.version,
      crypto.randomUUID(),
    );
  }
  async function post(confirmation: Confirmation): Promise<void> {
    const result = await api.postProposal(
      organization!.id,
      params.proposalId,
      confirmation.id,
      crypto.randomUUID(),
    );
    router.push(`/money/${result.entry_id}`);
  }
  return (
    <div className="page">
      <PageHeader
        eyebrow="Proposal workflow"
        title="Review financial event"
        description="Validation, confirmation, and posting remain separate."
        action={
          <ButtonLink href="/money" variant="secondary">
            Back to Money
          </ButtonLink>
        }
      />
      <ProposalWorkflow
        proposal={resource.data}
        organization={organization!}
        onValidate={validate}
        onConfirm={confirm}
        onPost={post}
      />
    </div>
  );
}
