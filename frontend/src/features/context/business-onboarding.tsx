"use client";

import { useState } from "react";

import { Button, Field, Notice } from "@/components/ui";
import { api } from "@/lib/api/client";

import { useFinancialSpace } from "./financial-space-provider";

export function BusinessOnboarding() {
  const { reloadOrganizations, selectBusiness } = useFinancialSpace();
  const [name, setName] = useState("");
  const [currency, setCurrency] = useState("");
  const [digits, setDigits] = useState("2");
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setSaving(true);
    setError("");
    try {
      const organization = await api.createOrganization({
        name,
        currency: currency.trim().toUpperCase(),
        minor_unit_digits: Number(digits),
      });
      await reloadOrganizations();
      selectBusiness(organization.id);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not create the business.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="onboarding">
      <div>
        <p className="eyebrow">Start with a business</p>
        <h1>Create your financial context</h1>
        <p>
          Chatbooks keeps every business ledger separate. You can add accounts and an open period
          next.
        </p>
      </div>
      <form className="form-panel" onSubmit={submit}>
        {error && <Notice tone="error">{error}</Notice>}
        <Field label="Business name">
          <input required value={name} onChange={(event) => setName(event.target.value)} />
        </Field>
        <div className="form-grid two">
          <Field label="Currency code" hint="Three uppercase letters, such as BDT or USD.">
            <input
              required
              maxLength={3}
              value={currency}
              onChange={(event) => setCurrency(event.target.value)}
            />
          </Field>
          <Field label="Decimal places">
            <select value={digits} onChange={(event) => setDigits(event.target.value)}>
              {[0, 1, 2, 3, 4, 5, 6].map((value) => (
                <option key={value}>{value}</option>
              ))}
            </select>
          </Field>
        </div>
        <Button disabled={saving}>{saving ? "Creating…" : "Create business"}</Button>
      </form>
    </div>
  );
}
