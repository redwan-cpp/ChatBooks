import { ButtonLink, EmptyState } from "@/components/ui";

export default function NotFound() {
  return (
    <main className="standalone-state">
      <EmptyState
        icon="chat"
        title="This page isn’t here"
        description="Return to the conversation and choose a financial task."
        action={<ButtonLink href="/chat">Back to Chat</ButtonLink>}
      />
    </main>
  );
}
