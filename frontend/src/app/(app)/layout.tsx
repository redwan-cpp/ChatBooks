import { AppShell } from "@/components/app-shell";
import { ProtectedRoute } from "@/features/auth/protected-route";
import { FinancialSpaceProvider } from "@/features/context/financial-space-provider";

export default function ApplicationLayout({ children }: { children: React.ReactNode }) {
  return (
    <ProtectedRoute>
      <FinancialSpaceProvider>
        <AppShell>{children}</AppShell>
      </FinancialSpaceProvider>
    </ProtectedRoute>
  );
}
