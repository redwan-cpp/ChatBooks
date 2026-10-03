"use client";

import { ErrorState } from "@/components/ui";

export default function GlobalError({ error, reset }: { error: Error; reset: () => void }) {
  return (
    <main className="standalone-state">
      <ErrorState error={error} onRetry={reset} />
    </main>
  );
}
