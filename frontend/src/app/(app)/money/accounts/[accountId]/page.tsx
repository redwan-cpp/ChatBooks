"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useState } from "react";

import { ErrorState, LoadingState, Notice, PageHeader } from "@/components/ui";
import { useFinancialSpace } from "@/features/context/financial-space-provider";
import { AccountDetail } from "@/features/money/account-detail";
import { useResource } from "@/hooks/use-resource";
import { api } from "@/lib/api/client";
import type { Organization } from "@/lib/api/types";

export default function AccountDetailPage() {
  const { organization } = useFinancialSpace();
  if (!organization) return null;
  return <BusinessAccountDetail organization={organization} />;
}

function BusinessAccountDetail({ organization }: { organization: Organization }) {
  const { accountId } = useParams<{ accountId: string }>();
  const [updating, setUpdating] = useState(false);
  const [updateError, setUpdateError] = useState("");
  const load = useCallback(async () => {
    const [account, report] = await Promise.all([
      api.account(organization.id, accountId),
      api.trialBalance(organization.id),
    ]);
    return {
      account,
      report,
      balance: report.accounts.find((item) => item.account_id === account.id) ?? null,
    };
  }, [accountId, organization.id]);
  const resource = useResource(load);

  async function toggle() {
    if (!resource.data) return;
    setUpdating(true);
    setUpdateError("");
    try {
      await api.updateAccount(organization.id, accountId, !resource.data.account.active);
      resource.reload();
    } catch (reason) {
      setUpdateError(reason instanceof Error ? reason.message : "Could not update the account.");
    } finally {
      setUpdating(false);
    }
  }

  return (
    <div className="page narrow-page account-detail-page">
      <Link className="back-link" href="/money">
        ← Back to Money
      </Link>
      <PageHeader
        eyebrow="Business account"
        title={resource.data?.account.name ?? "Account detail"}
        description="A focused view of the API-backed account and its current ledger balance."
      />
      {updateError && <Notice tone="error">{updateError}</Notice>}
      {resource.loading ? (
        <LoadingState label="Loading account detail" />
      ) : resource.error || !resource.data ? (
        <ErrorState
          error={resource.error ?? new Error("Account detail is unavailable.")}
          onRetry={resource.reload}
        />
      ) : (
        <AccountDetail
          account={resource.data.account}
          balance={resource.data.balance}
          report={resource.data.report}
          organization={organization}
          updating={updating}
          onToggle={() => void toggle()}
        />
      )}
    </div>
  );
}
