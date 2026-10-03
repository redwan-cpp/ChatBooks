"use client";

import { PageHeader } from "@/components/ui";
import { ReportsView } from "@/features/reports/reports-view";

export default function ReportsPage() {
  return (
    <div className="page">
      <PageHeader
        eyebrow="Verified financial data"
        title="Reports"
        description="Read financial statements and ledger detail calculated by the accounting engine."
      />
      <ReportsView />
    </div>
  );
}
