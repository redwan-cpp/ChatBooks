"use client";

import { useCallback, useState } from "react";

import {
  Badge,
  Button,
  EmptyState,
  ErrorState,
  Field,
  LoadingState,
  Notice,
} from "@/components/ui";
import { useFinancialSpace } from "@/features/context/financial-space-provider";
import { useResource } from "@/hooks/use-resource";
import { api } from "@/lib/api/client";
import { formatFinancialDate } from "@/lib/money";
import { allows } from "@/lib/permissions";

export function PeriodSetup() {
  const { organization } = useFinancialSpace();
  const load = useCallback(() => api.periods(organization!.id), [organization]);
  const resource = useResource(load);
  const [showForm, setShowForm] = useState(false);
  const [name, setName] = useState("");
  const [startsOn, setStartsOn] = useState("");
  const [endsOn, setEndsOn] = useState("");
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const canManage = allows(organization?.role, "manage_period");
  const canLock = allows(organization?.role, "lock_period");

  async function create(event: React.FormEvent) {
    event.preventDefault();
    setSaving(true);
    setError("");
    try {
      await api.createPeriod(organization!.id, { name, starts_on: startsOn, ends_on: endsOn });
      setName("");
      setStartsOn("");
      setEndsOn("");
      setShowForm(false);
      resource.reload();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not create the period.");
    } finally {
      setSaving(false);
    }
  }
  async function lock(periodId: string) {
    if (!window.confirm("Lock this period? New postings dated inside it will be rejected.")) return;
    setError("");
    try {
      await api.lockPeriod(organization!.id, periodId);
      resource.reload();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not lock the period.");
    }
  }

  if (resource.loading) return <LoadingState label="Loading accounting periods" />;
  if (resource.error) return <ErrorState error={resource.error} onRetry={resource.reload} />;
  const periods = resource.data ?? [];
  return (
    <section className="section-stack">
      <div className="section-heading">
        <div>
          <h2>Accounting periods</h2>
          <p>Entries can post only into an open period. Locking is permanent in M4.</p>
        </div>
        {canManage && (
          <Button variant="secondary" onClick={() => setShowForm((value) => !value)}>
            {showForm ? "Cancel" : "Add period"}
          </Button>
        )}
      </div>
      {error && <Notice tone="error">{error}</Notice>}
      {showForm && (
        <form className="inline-form" onSubmit={create}>
          <Field label="Name">
            <input required value={name} onChange={(event) => setName(event.target.value)} />
          </Field>
          <Field label="Starts">
            <input
              required
              type="date"
              value={startsOn}
              onChange={(event) => setStartsOn(event.target.value)}
            />
          </Field>
          <Field label="Ends">
            <input
              required
              type="date"
              value={endsOn}
              onChange={(event) => setEndsOn(event.target.value)}
            />
          </Field>
          <Button disabled={saving}>{saving ? "Adding…" : "Add period"}</Button>
        </form>
      )}
      {periods.length === 0 ? (
        <EmptyState
          icon="activity"
          title="No accounting periods"
          description="Create an open period before validating and posting financial activity."
        />
      ) : (
        <div className="data-list">
          {periods.map((period) => (
            <div className="data-row" key={period.id}>
              <span>
                <strong>{period.name}</strong>
                <small>
                  {formatFinancialDate(period.starts_on)} — {formatFinancialDate(period.ends_on)}
                </small>
              </span>
              <Badge tone={period.locked ? "neutral" : "success"}>
                {period.locked ? "Locked" : "Open"}
              </Badge>
              {canLock && !period.locked && (
                <Button variant="quiet" onClick={() => void lock(period.id)}>
                  Lock period
                </Button>
              )}
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
