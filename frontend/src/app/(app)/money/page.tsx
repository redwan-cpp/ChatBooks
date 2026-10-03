"use client";

import { ButtonLink, PageHeader } from "@/components/ui";
import { useFinancialSpace } from "@/features/context/financial-space-provider";
import { MoneyWorkspace } from "@/features/money/money-views";
import { allows } from "@/lib/permissions";

export default function MoneyPage() {
  const { organization } = useFinancialSpace();
  if (!organization) return null;

  return (
    <div className="page">
      <PageHeader
        eyebrow="Business money"
        title="Money"
        description="See where the business stands, understand what came in and went out, and record new activity through a reviewable proposal."
        action={
          allows(organization.role, "create_proposal") ? (
            <ButtonLink href="/money/proposals/new">Record an event</ButtonLink>
          ) : undefined
        }
      />
      <MoneyWorkspace organization={organization} />
    </div>
  );
}
