"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";

import { api } from "@/lib/api/client";
import type { Organization } from "@/lib/api/types";

import { useAuth } from "../auth/auth-provider";

export type FinancialSpace =
  { kind: "personal" } | { kind: "business"; organizationId: string | null };

interface FinancialSpaceContextValue {
  space: FinancialSpace;
  organizations: Organization[];
  organization: Organization | null;
  loading: boolean;
  error: Error | null;
  selectPersonal: () => void;
  selectBusiness: (organizationId: string | null) => void;
  reloadOrganizations: () => Promise<Organization[]>;
}

const FinancialSpaceContext = createContext<FinancialSpaceContextValue | null>(null);
const STORAGE_KEY = "chatbook_financial_space";

export function FinancialSpaceProvider({ children }: { children: React.ReactNode }) {
  const { status } = useAuth();
  const [space, setSpace] = useState<FinancialSpace>({ kind: "business", organizationId: null });
  const [organizations, setOrganizations] = useState<Organization[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const reloadOrganizations = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const items = await api.organizations();
      setOrganizations(items);
      setSpace((current) => {
        if (current.kind === "personal") return current;
        const currentExists = items.some((item) => item.id === current.organizationId);
        return {
          kind: "business",
          organizationId: currentExists ? current.organizationId : (items[0]?.id ?? null),
        };
      });
      return items;
    } catch (reason) {
      setError(reason instanceof Error ? reason : new Error("Could not load organizations."));
      throw reason;
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (status !== "authenticated") return;
    const stored = window.localStorage.getItem(STORAGE_KEY);
    void Promise.resolve().then(() => {
      if (stored === "personal") setSpace({ kind: "personal" });
      else if (stored?.startsWith("business:")) {
        setSpace({ kind: "business", organizationId: stored.slice("business:".length) || null });
      }
      return reloadOrganizations().catch(() => undefined);
    });
  }, [reloadOrganizations, status]);

  const selectPersonal = useCallback(() => {
    setSpace({ kind: "personal" });
    window.localStorage.setItem(STORAGE_KEY, "personal");
  }, []);
  const selectBusiness = useCallback((organizationId: string | null) => {
    setSpace({ kind: "business", organizationId });
    window.localStorage.setItem(STORAGE_KEY, `business:${organizationId ?? ""}`);
  }, []);
  const organization =
    space.kind === "business"
      ? (organizations.find((item) => item.id === space.organizationId) ?? null)
      : null;

  const value = useMemo(
    () => ({
      space,
      organizations,
      organization,
      loading,
      error,
      selectPersonal,
      selectBusiness,
      reloadOrganizations,
    }),
    [
      space,
      organizations,
      organization,
      loading,
      error,
      selectPersonal,
      selectBusiness,
      reloadOrganizations,
    ],
  );
  return <FinancialSpaceContext.Provider value={value}>{children}</FinancialSpaceContext.Provider>;
}

export function useFinancialSpace(): FinancialSpaceContextValue {
  const context = useContext(FinancialSpaceContext);
  if (!context) throw new Error("useFinancialSpace must be used inside FinancialSpaceProvider.");
  return context;
}
