"use client";

import { useState } from "react";

import { Button, Field, Notice } from "@/components/ui";
import type { Project, ProjectPayload, ProjectStatus } from "@/lib/api/types";
import { decimalFromMinorUnits, minorUnitsFromDecimal } from "@/lib/money";

const statuses: ProjectStatus[] = ["planned", "active", "completed", "cancelled"];

export function ProjectForm({
  project,
  minorUnitDigits,
  onSubmit,
}: {
  project?: Project;
  minorUnitDigits: number;
  onSubmit: (value: ProjectPayload) => Promise<void>;
}) {
  const [name, setName] = useState(project?.name ?? "");
  const [description, setDescription] = useState(project?.description ?? "");
  const [client, setClient] = useState(project?.client ?? "");
  const [expectedRevenue, setExpectedRevenue] = useState(
    decimalFromMinorUnits(project?.expected_revenue ?? null, minorUnitDigits),
  );
  const [budget, setBudget] = useState(
    decimalFromMinorUnits(project?.budget ?? null, minorUnitDigits),
  );
  const [startsOn, setStartsOn] = useState(project?.starts_on ?? "");
  const [endsOn, setEndsOn] = useState(project?.ends_on ?? "");
  const [status, setStatus] = useState<ProjectStatus>(project?.status ?? "planned");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setSaving(true);
    try {
      if (startsOn && endsOn && startsOn > endsOn) {
        throw new Error("The end date must be on or after the start date.");
      }
      await onSubmit({
        name,
        description,
        client: client || null,
        expected_revenue: expectedRevenue
          ? minorUnitsFromDecimal(expectedRevenue, minorUnitDigits)
          : null,
        budget: budget ? minorUnitsFromDecimal(budget, minorUnitDigits) : null,
        starts_on: startsOn || null,
        ends_on: endsOn || null,
        status,
      });
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not save the project.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <form className="project-form section-stack" onSubmit={submit}>
      {error && <Notice tone="error">{error}</Notice>}
      <section className="surface form-section">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Project identity</p>
            <h2>What are you working on?</h2>
          </div>
        </div>
        <div className="form-grid two">
          <Field label="Project name">
            <input
              required
              maxLength={200}
              value={name}
              onChange={(event) => setName(event.target.value)}
            />
          </Field>
          <Field label="Client" hint="Optional">
            <input value={client} onChange={(event) => setClient(event.target.value)} />
          </Field>
        </div>
        <Field label="Context" hint="A short description helps collaborators understand the work.">
          <textarea
            rows={4}
            value={description}
            onChange={(event) => setDescription(event.target.value)}
          />
        </Field>
      </section>

      <section className="surface form-section">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Planning values</p>
            <h2>Set expectations</h2>
            <p>
              These values describe the plan. They do not change the ledger or report actual
              results.
            </p>
          </div>
        </div>
        <div className="form-grid two">
          <Field label="Expected revenue" hint="Optional plan amount">
            <input
              inputMode="decimal"
              placeholder="0.00"
              value={expectedRevenue}
              onChange={(event) => setExpectedRevenue(event.target.value)}
            />
          </Field>
          <Field label="Budget" hint="Optional plan amount">
            <input
              inputMode="decimal"
              placeholder="0.00"
              value={budget}
              onChange={(event) => setBudget(event.target.value)}
            />
          </Field>
          <Field label="Start date" hint="Optional">
            <input
              type="date"
              value={startsOn}
              onChange={(event) => setStartsOn(event.target.value)}
            />
          </Field>
          <Field label="End date" hint="Optional">
            <input type="date" value={endsOn} onChange={(event) => setEndsOn(event.target.value)} />
          </Field>
          <Field label="Status">
            <select
              value={status}
              onChange={(event) => setStatus(event.target.value as ProjectStatus)}
            >
              {statuses.map((value) => (
                <option key={value} value={value}>
                  {value[0]?.toUpperCase()}
                  {value.slice(1)}
                </option>
              ))}
            </select>
          </Field>
        </div>
      </section>

      <div className="form-actions">
        <Button type="submit" disabled={saving}>
          {saving ? "Saving…" : project ? "Save changes" : "Create project"}
        </Button>
      </div>
    </form>
  );
}
