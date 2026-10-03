"use client";

import { useState } from "react";

import { Button, Field, Notice } from "@/components/ui";
import type { Account, Project } from "@/lib/api/types";
import { minorUnitsFromDecimal } from "@/lib/money";

interface DraftLine {
  accountId: string;
  side: "debit" | "credit";
  amount: string;
  projectId: string;
}
const newLine = (side: "debit" | "credit", projectId = ""): DraftLine => ({
  accountId: "",
  side,
  amount: "",
  projectId,
});

export interface ProposalFormValue {
  entry_date: string;
  description: string;
  lines: Array<{ account_id: string; debit: number; credit: number; project_id: string | null }>;
}

export function ProposalForm({
  accounts,
  projects,
  minorUnitDigits,
  initialProjectId = "",
  onSubmit,
}: {
  accounts: Account[];
  projects: Project[];
  minorUnitDigits: number;
  initialProjectId?: string;
  onSubmit: (value: ProposalFormValue) => Promise<void>;
}) {
  const [entryDate, setEntryDate] = useState(new Date().toISOString().slice(0, 10));
  const [description, setDescription] = useState("");
  const [lines, setLines] = useState<DraftLine[]>([
    newLine("debit", initialProjectId),
    newLine("credit", initialProjectId),
  ]);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  function update(index: number, change: Partial<DraftLine>) {
    setLines((current) =>
      current.map((line, position) => (position === index ? { ...line, ...change } : line)),
    );
  }
  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setError("");
    setSaving(true);
    try {
      const payloadLines = lines.map((line) => {
        const amount = minorUnitsFromDecimal(line.amount, minorUnitDigits);
        return {
          account_id: line.accountId,
          debit: line.side === "debit" ? amount : 0,
          credit: line.side === "credit" ? amount : 0,
          project_id: line.projectId || null,
        };
      });
      await onSubmit({ entry_date: entryDate, description, lines: payloadLines });
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not create the proposal.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <form className="proposal-form" onSubmit={submit}>
      {error && <Notice tone="error">{error}</Notice>}
      <div className="form-grid two">
        <Field label="Financial date">
          <input
            type="date"
            required
            value={entryDate}
            onChange={(event) => setEntryDate(event.target.value)}
          />
        </Field>
        <Field label="Description">
          <input
            required
            placeholder="What happened?"
            value={description}
            onChange={(event) => setDescription(event.target.value)}
          />
        </Field>
      </div>
      <div className="proposal-lines-heading">
        <div>
          <h2>Money movement</h2>
          <p>Add at least one debit and one credit. Chatbooks will validate the balance.</p>
        </div>
        <Button
          type="button"
          variant="secondary"
          onClick={() => setLines((current) => [...current, newLine("debit", initialProjectId)])}
        >
          Add line
        </Button>
      </div>
      <div className="proposal-lines">
        {lines.map((line, index) => (
          <div key={index} className="proposal-line">
            <span className="line-number">{index + 1}</span>
            <Field label="Account">
              <select
                required
                value={line.accountId}
                onChange={(event) => update(index, { accountId: event.target.value })}
              >
                <option value="">Choose account</option>
                {accounts
                  .filter((account) => account.active)
                  .map((account) => (
                    <option key={account.id} value={account.id}>
                      {account.code} · {account.name}
                    </option>
                  ))}
              </select>
            </Field>
            <Field label="Side">
              <select
                value={line.side}
                onChange={(event) =>
                  update(index, { side: event.target.value as "debit" | "credit" })
                }
              >
                <option value="debit">Debit</option>
                <option value="credit">Credit</option>
              </select>
            </Field>
            <Field label="Amount">
              <input
                inputMode="decimal"
                required
                placeholder="0.00"
                value={line.amount}
                onChange={(event) => update(index, { amount: event.target.value })}
              />
            </Field>
            <Field label="Project">
              <select
                value={line.projectId}
                onChange={(event) => update(index, { projectId: event.target.value })}
              >
                <option value="">No project</option>
                {projects.map((project) => (
                  <option key={project.id} value={project.id}>
                    {project.name}
                  </option>
                ))}
              </select>
            </Field>
            {lines.length > 2 && (
              <button
                className="icon-button remove-line"
                type="button"
                aria-label={`Remove line ${index + 1}`}
                onClick={() =>
                  setLines((current) => current.filter((_, position) => position !== index))
                }
              >
                ×
              </button>
            )}
          </div>
        ))}
      </div>
      <Notice>
        The proposal has no ledger effect until it is validated, explicitly confirmed by an
        authorized user, and posted.
      </Notice>
      <div className="form-actions">
        <Button type="submit" disabled={saving || accounts.length < 2}>
          {saving ? "Creating proposal…" : "Create proposal"}
        </Button>
      </div>
    </form>
  );
}
