import { EmptyState } from "@/components/ui";
import type { AuditEvent } from "@/lib/api/types";
import { formatTimestamp } from "@/lib/money";

function titleCase(value: string): string {
  return value
    .split(/[._]/)
    .map((word) => `${word.slice(0, 1).toUpperCase()}${word.slice(1).toLowerCase()}`)
    .join(" ");
}

function eventLabel(event: AuditEvent): string {
  const value = event.event_type.toLowerCase();
  if (value === "confirmations.insert") return "Transaction confirmed";
  if (value === "validations.insert") return "Proposal validated";
  if (value === "transactions.insert") return "Proposal created";
  if (value === "transaction_lines.insert") return "Proposal line recorded";
  if (value === "journal_lines.insert") return "Journal line recorded";
  if (value === "journal_entries.update" && event.new_state?.state === "posted") {
    return "Journal entry posted";
  }
  const match = /^(.+)\.(insert|update)$/.exec(value);
  if (match) {
    const subject = titleCase(match[1] ?? "record");
    return `${subject} ${match[2] === "insert" ? "created" : "updated"}`;
  }
  return titleCase(event.event_type);
}

export function ActivityList({
  events,
  currentUserId,
}: {
  events: AuditEvent[];
  currentUserId: string;
}) {
  if (events.length === 0) {
    return (
      <EmptyState
        icon="activity"
        title="No audit activity"
        description="Authorized financial and organization changes will appear here as immutable audit events."
      />
    );
  }
  return (
    <ol className="audit-list">
      {events.map((event) => (
        <li className="audit-event" key={event.sequence}>
          <span className="audit-marker" aria-hidden="true" />
          <div className="audit-copy">
            <div className="audit-title-line">
              <strong>{eventLabel(event)}</strong>
              <span>#{event.sequence}</span>
            </div>
            <p>
              {event.entity_type.replaceAll("_", " ")} ·{" "}
              <span className="code-chip">{event.entity_id.slice(0, 12)}</span>
            </p>
            <p className="audit-meta">
              {event.actor_id === currentUserId ? "You" : `Actor ${event.actor_id.slice(0, 8)}`} ·{" "}
              {formatTimestamp(event.occurred_at)}
            </p>
            <details>
              <summary>View recorded details</summary>
              <div className="audit-detail-grid">
                {event.previous_state && (
                  <div>
                    <h3>Previous state</h3>
                    <pre>{JSON.stringify(event.previous_state, null, 2)}</pre>
                  </div>
                )}
                {event.new_state && (
                  <div>
                    <h3>New state</h3>
                    <pre>{JSON.stringify(event.new_state, null, 2)}</pre>
                  </div>
                )}
                <div>
                  <h3>Metadata</h3>
                  <pre>{JSON.stringify(event.metadata, null, 2)}</pre>
                </div>
              </div>
            </details>
          </div>
        </li>
      ))}
    </ol>
  );
}
