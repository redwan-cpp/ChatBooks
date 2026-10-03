"use client";

import Link from "next/link";
import { useState } from "react";

import { Badge, Button, Modal, Notice } from "@/components/ui";
import type { Confirmation, Proposal, Validation } from "@/lib/api/types";
import { formatFinancialDate, formatMoney, formatTimestamp } from "@/lib/money";
import { allows } from "@/lib/permissions";
import type { Organization } from "@/lib/api/types";

export function ProposalWorkflow({
  proposal,
  organization,
  onValidate,
  onConfirm,
  onPost,
}: {
  proposal: Proposal;
  organization: Organization;
  onValidate: () => Promise<Validation>;
  onConfirm: (validation: Validation) => Promise<Confirmation>;
  onPost: (confirmation: Confirmation) => Promise<void>;
}) {
  const [validation, setValidation] = useState<Validation | null>(null);
  const [confirmation, setConfirmation] = useState<Confirmation | null>(null);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [accepted, setAccepted] = useState(false);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  async function validate() {
    setBusy("validate");
    setError("");
    try {
      setValidation(await onValidate());
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Validation failed.");
    } finally {
      setBusy("");
    }
  }
  async function confirm() {
    if (!validation || !accepted) return;
    setBusy("confirm");
    setError("");
    try {
      setConfirmation(await onConfirm(validation));
      setConfirmOpen(false);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Confirmation failed.");
    } finally {
      setBusy("");
    }
  }
  async function post() {
    if (!confirmation) return;
    setBusy("post");
    setError("");
    try {
      await onPost(confirmation);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Posting failed.");
    } finally {
      setBusy("");
    }
  }
  const steps = ["Draft", "Validate", "Review", "Confirm", "Post"];
  const progress = proposal.posted_entry_id ? 5 : confirmation ? 4 : validation ? 2 : 1;
  return (
    <div className="workflow">
      <ol className="workflow-steps" aria-label="Proposal progress">
        {steps.map((step, index) => {
          const complete = index < progress;
          const current = index === progress;
          return (
            <li
              key={step}
              className={complete ? "complete" : current ? "current" : undefined}
              aria-current={current ? "step" : undefined}
            >
              <span>{complete ? "✓" : index + 1}</span>
              {step}
            </li>
          );
        })}
      </ol>
      {error && <Notice tone="error">{error}</Notice>}
      <section className="proposal-review">
        <div className="proposal-review-head">
          <div>
            <Badge tone={proposal.reverses_entry_id ? "warning" : "neutral"}>
              {proposal.reverses_entry_id ? "Reversal proposal" : "Manual proposal"}
            </Badge>
            <h2>{proposal.description}</h2>
            <p>
              {formatFinancialDate(proposal.entry_date)} · version {proposal.version}
            </p>
          </div>
          <strong>
            {validation
              ? formatMoney(validation.debit_total, proposal.currency, proposal.minor_unit_digits)
              : "Pending validation"}
          </strong>
        </div>
        <div className="journal-lines">
          {proposal.lines.map((line) => (
            <div key={line.position}>
              <span>
                <small>{line.debit ? "Debit" : "Credit"}</small>
                <strong>{line.name}</strong>
                <em>
                  {line.code}
                  {line.project_id ? " · project assigned" : ""}
                </em>
              </span>
              <strong>
                {formatMoney(
                  line.debit || line.credit,
                  proposal.currency,
                  proposal.minor_unit_digits,
                )}
              </strong>
            </div>
          ))}
        </div>
      </section>
      <div className="workflow-actions">
        {proposal.posted_entry_id ? (
          <Link className="button button-primary" href={`/money/${proposal.posted_entry_id}`}>
            View posted entry
          </Link>
        ) : !validation ? (
          allows(organization.role, "create_proposal") ? (
            <Button onClick={() => void validate()} disabled={busy !== ""}>
              {busy === "validate" ? "Validating…" : "Validate proposal"}
            </Button>
          ) : (
            <Notice>Your role does not allow proposal validation.</Notice>
          )
        ) : !confirmation ? (
          allows(organization.role, "confirm_proposal") ? (
            <Button onClick={() => setConfirmOpen(true)}>Review and confirm</Button>
          ) : (
            <Notice>An accountant or administrator must confirm this validated proposal.</Notice>
          )
        ) : allows(organization.role, "post_journal") ? (
          <Button onClick={() => void post()} disabled={busy !== ""}>
            {busy === "post" ? "Posting…" : "Post to ledger"}
          </Button>
        ) : (
          <Notice>An accountant or administrator must post this confirmed proposal.</Notice>
        )}
      </div>
      {validation && (
        <section className="validation-evidence">
          <span>
            <small>Validation</small>
            <strong>Balanced and eligible</strong>
          </span>
          <span>
            <small>Debits</small>
            <strong>
              {formatMoney(validation.debit_total, proposal.currency, proposal.minor_unit_digits)}
            </strong>
          </span>
          <span>
            <small>Credits</small>
            <strong>
              {formatMoney(validation.credit_total, proposal.currency, proposal.minor_unit_digits)}
            </strong>
          </span>
        </section>
      )}
      {confirmation && (
        <Notice>
          Confirmed by actor {confirmation.actor_id.slice(0, 8)} on{" "}
          {formatTimestamp(confirmation.confirmed_at)}. Confirmation alone has not changed the
          ledger.
        </Notice>
      )}
      <Modal
        open={confirmOpen}
        title="Confirm this exact proposal"
        description="Confirmation binds your authenticated identity to the displayed version. Posting remains a separate action."
        onClose={() => setConfirmOpen(false)}
      >
        <div className="confirmation-summary">
          <p>
            <strong>{proposal.description}</strong>
          </p>
          <p>
            {formatFinancialDate(proposal.entry_date)} · version {proposal.version}
          </p>
          <p>
            {validation &&
              formatMoney(validation.debit_total, proposal.currency, proposal.minor_unit_digits)}
          </p>
        </div>
        <label className="check-row">
          <input
            type="checkbox"
            checked={accepted}
            onChange={(event) => setAccepted(event.target.checked)}
          />
          <span>I reviewed the accounts, amount, date, project context, and proposal version.</span>
        </label>
        <div className="button-row">
          <Button variant="secondary" onClick={() => setConfirmOpen(false)}>
            Cancel
          </Button>
          <Button disabled={!accepted || busy !== ""} onClick={() => void confirm()}>
            {busy === "confirm" ? "Confirming…" : "Confirm proposal"}
          </Button>
        </div>
      </Modal>
    </div>
  );
}
