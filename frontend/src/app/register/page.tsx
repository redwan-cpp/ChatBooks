import { Suspense } from "react";

import { LoadingState } from "@/components/ui";
import { AuthScreen } from "@/features/auth/auth-screen";

export default function RegisterPage() {
  return (
    <Suspense
      fallback={
        <main className="auth-loading">
          <LoadingState />
        </main>
      }
    >
      <AuthScreen mode="register" />
    </Suspense>
  );
}
