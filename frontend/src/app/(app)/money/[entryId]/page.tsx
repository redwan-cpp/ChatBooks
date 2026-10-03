"use client";

import { useParams, useRouter } from "next/navigation";
import { useCallback, useState } from "react";

import {
  Badge,
  Button,
  ButtonLink,
  ErrorState,
  Field,
  LoadingState,
  Modal,
  Notice,
  PageHeader,
} from "@/components/ui";
import { useFinancialSpace } from "@/features/context/financial-space-provider";
import { useResource } from "@/hooks/use-resource";
import { api } from "@/lib/api/client";
import { formatFinancialDate, formatMoney, formatTimestamp } from "@/lib/money";
import { allows } from "@/lib/permissions";

export default function MoneyDetailPage() {
  const params = useParams<{ entryId: string }>();
  const router = useRouter();
  const { organization } = useFinancialSpace();
  const canAudit = allows(organization?.role, "view_audit");
  const load = useCallback(
    () =>
      Promise.all([
        api.journalEntry(organization!.id, params.entryId),
        api.projects(organization!.id, 0, 100),
        canAudit ? api.auditEvents(organization!.id, 0, 50, params.entryId) : Promise.resolve(null),
      ]),
    [canAudit, organization, params.entryId],
  );
  const resource = useResource(load);
  const [reversalOpen, setReversalOpen] = useState(false);
  const [date, setDate] = useState("");
  const [reason, setReason] = useState("");
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  async function reverse(event: React.FormEvent) {
    event.preventDefault();
    setSaving(true);
    setError("");
    try {
      const proposal = await api.createReversal(organization!.id, params.entryId, {
        entry_date: date,
        reason,
      });
      router.push(`/money/proposals/${proposal.id}`);
    } catch (reasonValue) {
      setError(
        reasonValue instanceof Error
          ? reasonValue.message
          : "Could not create the reversal proposal.",
      );
    } finally {
      setSaving(false);
    }
  }

  if (resource.loading)
    return (
      <div className="page">
        <LoadingState label="Loading transaction" />
      </div>
    );
  if (resource.error || !resource.data)
    return (
      <div className="page">
        <ErrorState
          error={resource.error ?? new Error("Transaction not found.")}
          onRetry={resource.reload}
        />
      </div>
    );
  const [entry, projectPage, auditPage] = resource.data;
  const projectNames = new Map(projectPage.items.map((project) => [project.id, project.name]));
  return (
    <div className="page detail-page">
      <PageHeader
        eyebrow={entry.reverses_entry_id ? "Posted reversal" : "Posted activity"}
        title={entry.description}
        description={`${formatFinancialDate(entry.entry_date)} · ${entry.line_count} accounting lines`}
        action={
          <div className="button-row">
            <ButtonLink href="/money" variant="secondary">
              Back
            </ButtonLink>
            {allows(organization?.role, "reverse_entry") && (
              <Button variant="danger" onClick={() => setReversalOpen(true)}>
                Reverse
              </Button>
            )}
          </div>
        }
      />
      <section className="amount-hero">
        <small>Entry value</small>
        <strong>
          {formatMoney(entry.debit_total, organization!.currency, organization!.minor_unit_digits)}
        </strong>
        <Badge tone="success">Posted</Badge>
      </section>
      <section className="detail-grid">
        <div>
          <small>Date</small>
          <strong>{formatFinancialDate(entry.entry_date)}</strong>
        </div>
        <div>
          <small>Project</small>
          <strong>
            {entry.project_ids.length
              ? entry.project_ids.map((id) => projectNames.get(id) ?? "Project").join(", ")
              : "No project"}
          </strong>
        </div>
        <div>
          <small>State</small>
          <strong>{entry.reverses_entry_id ? "Compensating reversal" : "Posted entry"}</strong>
        </div>
        <div>
          <small>Reference</small>
          <strong className="mono">{entry.id.slice(0, 12)}</strong>
        </div>
      </section>
      <details className="disclosure" open>
        <summary>
          <span>
            <strong>Money movement</strong>
            <small>Account-level detail</small>
          </span>
          <span>Show accounting</span>
        </summary>
        <div className="journal-lines">
          {entry.lines.map((line) => (
            <div key={`${line.position}-${line.account_id}`}>
              <span>
                <small>{line.debit ? "Debit" : "Credit"}</small>
                <strong>{line.account_name}</strong>
                <em>
                  {line.code} · {line.account_type}
                </em>
              </span>
              <strong>
                {formatMoney(
                  line.debit || line.credit,
                  organization!.currency,
                  organization!.minor_unit_digits,
                )}
              </strong>
            </div>
          ))}
        </div>
      </details>
      <details className="disclosure">
        <summary>
          <span>
            <strong>Accounting provenance</strong>
            <small>Proposal, confirmation, period, and audit</small>
          </span>
          <span>Show evidence</span>
        </summary>
        <dl className="provenance">
          <div>
            <dt>Proposal</dt>
            <dd className="mono">{entry.transaction_id}</dd>
          </div>
          <div>
            <dt>Confirmation</dt>
            <dd className="mono">{entry.confirmation_id}</dd>
          </div>
          <div>
            <dt>Period</dt>
            <dd className="mono">{entry.period_id}</dd>
          </div>
          {entry.reverses_entry_id && (
            <div>
              <dt>Reverses</dt>
              <dd className="mono">{entry.reverses_entry_id}</dd>
            </div>
          )}
        </dl>
        {canAudit && auditPage && (
          <div className="mini-timeline">
            {auditPage.items.map((event) => (
              <div key={event.sequence}>
                <span />
                <p>
                  <strong>{String(event.metadata.operation ?? event.event_type)}</strong>
                  <small>
                    {formatTimestamp(event.occurred_at)} · actor {event.actor_id.slice(0, 8)}
                  </small>
                </p>
              </div>
            ))}
          </div>
        )}
        {!canAudit && (
          <Notice>
            Audit evidence is available to accountants and organization administrators.
          </Notice>
        )}
      </details>
      <Modal
        open={reversalOpen}
        title="Create a reversal proposal"
        description="The original entry will remain visible. The reversal must still be validated, confirmed, and posted."
        onClose={() => setReversalOpen(false)}
      >
        <form className="form-panel" onSubmit={reverse}>
          {error && <Notice tone="error">{error}</Notice>}
          <Field label="Reversal date">
            <input
              required
              type="date"
              min={entry.entry_date}
              value={date}
              onChange={(event) => setDate(event.target.value)}
            />
          </Field>
          <Field label="Reason">
            <textarea
              required
              rows={3}
              value={reason}
              onChange={(event) => setReason(event.target.value)}
            />
          </Field>
          <div className="button-row">
            <Button type="button" variant="secondary" onClick={() => setReversalOpen(false)}>
              Cancel
            </Button>
            <Button variant="danger" disabled={saving}>
              {saving ? "Creating…" : "Create reversal proposal"}
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
