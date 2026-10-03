"use client";

import Link from "next/link";

import { Badge, Notice, PageHeader } from "@/components/ui";
import { useFinancialSpace } from "@/features/context/financial-space-provider";
import { PeriodSetup } from "@/features/money/period-setup";

export default function SettingsPage() {
  const { organization } = useFinancialSpace();
  if (!organization) return null;
  return (
    <div className="page">
      <PageHeader
        eyebrow="Business context"
        title="Settings"
        description="Manage the financial context and reveal accounting setup only when it is needed."
      />
      <div className="settings-layout">
        <section className="surface space-summary">
          <div className="section-heading">
            <div>
              <p className="eyebrow">Current space</p>
              <h2>{organization.name}</h2>
            </div>
            <Badge tone="success">{organization.role.toLowerCase()}</Badge>
          </div>
          <dl>
            <div>
              <dt>Currency</dt>
              <dd>{organization.currency}</dd>
            </div>
            <div>
              <dt>Decimal places</dt>
              <dd>{organization.minor_unit_digits}</dd>
            </div>
          </dl>
          <Notice>
            Backend authorization remains authoritative. Controls shown here cannot grant financial
            permission.
          </Notice>
        </section>
        <section className="surface settings-guide">
          <p className="eyebrow">Where things live</p>
          <h2>Financial setup without an ERP menu</h2>
          <p>
            Account management stays under <Link href="/money">Money</Link>. Period controls remain
            here because they are advanced accounting setup.
          </p>
        </section>
      </div>
      <details className="settings-disclosure" open>
        <summary>
          <span>
            <strong>Accounting periods</strong>
            <small>Advanced posting controls</small>
          </span>
          <span>Show setup</span>
        </summary>
        <div className="settings-disclosure-body">
          <PeriodSetup />
        </div>
      </details>
    </div>
  );
}
