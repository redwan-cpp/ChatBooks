"use client";

import Link from "next/link";
import { useState } from "react";

import { Icon, type IconName } from "@/components/icons";
import { MoneyCompanion } from "@/components/money-companion";
import { Badge, Notice } from "@/components/ui";

interface ConversationDraft {
  id: number;
  text: string;
}

const businessIntents: Array<{
  title: string;
  description: string;
  href: string;
  icon: IconName;
}> = [
  {
    title: "Review money activity",
    description: "See financial events already posted to this business.",
    href: "/activity",
    icon: "activity",
  },
  {
    title: "Understand the numbers",
    description: "Open reports calculated by the accounting engine.",
    href: "/reports",
    icon: "reports",
  },
  {
    title: "Record an event manually",
    description: "Use the existing structured proposal and review flow.",
    href: "/money/proposals/new",
    icon: "plus",
  },
];

const personalIntents: Array<{
  title: string;
  description: string;
  href: string;
  icon: IconName;
}> = [
  {
    title: "Personal Money",
    description: "Coming after the Personal Finance Foundation.",
    href: "/money",
    icon: "money",
  },
  {
    title: "Personal Activity",
    description: "No personal financial records are available yet.",
    href: "/activity",
    icon: "activity",
  },
  {
    title: "Personal Reports",
    description: "Reports will appear only after ledger-backed APIs exist.",
    href: "/reports",
    icon: "reports",
  },
];

export function ChatWorkspace({
  spaceKind,
  spaceName,
}: {
  spaceKind: "personal" | "business";
  spaceName: string;
}) {
  const [draft, setDraft] = useState("");
  const [drafts, setDrafts] = useState<ConversationDraft[]>([]);
  const [notice, setNotice] = useState("");
  const intents = spaceKind === "business" ? businessIntents : personalIntents;

  function submit() {
    const text = draft.trim();
    if (!text) return;
    setDrafts((current) => [...current, { id: Date.now(), text }]);
    setDraft("");
    setNotice(
      "This message was kept only in the current screen. AI financial actions and conversation storage are not enabled, so nothing was sent or changed.",
    );
  }

  return (
    <div className="conversation-page">
      <header className="conversation-header">
        <div>
          <span className={`context-dot context-dot-${spaceKind}`} aria-hidden="true" />
          <span>
            <small>{spaceKind === "business" ? "Business space" : "Personal space"}</small>
            <strong>{spaceName}</strong>
          </span>
        </div>
        <Badge tone="neutral">AI actions unavailable</Badge>
      </header>

      <div className="conversation-layout">
        <section className="conversation-main" aria-labelledby="conversation-title">
          <div className="conversation-intro">
            <div className="conversation-intro-copy">
              <p className="eyebrow">Financial conversation</p>
              <h1 id="conversation-title">What do you want to do with your money?</h1>
              <p>
                {spaceKind === "business"
                  ? "Choose a supported path today. Future conversational help will still create a proposal for your review—it will never post directly to the ledger."
                  : "Explore the Personal shell without creating financial records. Personal financial capabilities will arrive only after their ledger-backed foundation is implemented."}
              </p>
            </div>
            <div className="chat-companion-stage" aria-hidden="true">
              <span>
                {spaceKind === "business" ? "Let’s make it clear." : "Personal is on its way."}
              </span>
              <MoneyCompanion mood="bright" />
            </div>
          </div>

          <ol className="message-history" aria-label="Conversation history" aria-live="polite">
            <li className="message message-product">
              <span className="message-avatar" aria-hidden="true">
                <span />
              </span>
              <div>
                <span className="message-author">Chatbooks</span>
                <p>
                  {spaceKind === "business"
                    ? "Conversational financial assistance is not connected yet. You can still use the verified BUSINESS workflows below."
                    : "Conversational financial assistance is not connected yet. The links below show where future Personal capabilities will live; they do not create or display personal financial data."}
                </p>
              </div>
            </li>
            {drafts.map((item) => (
              <li className="message message-user" key={item.id}>
                <div>
                  <span className="message-author">You · not sent</span>
                  <p>{item.text}</p>
                </div>
              </li>
            ))}
          </ol>

          {drafts.length === 0 && (
            <div className="intent-list" aria-label="Supported paths">
              {intents.map((intent) => (
                <Link key={intent.title} href={intent.href}>
                  <Icon name={intent.icon} />
                  <span>
                    <strong>{intent.title}</strong>
                    <small>{intent.description}</small>
                  </span>
                  <Icon name="arrow" />
                </Link>
              ))}
            </div>
          )}

          <div className="conversation-composer-wrap">
            {notice && <Notice>{notice}</Notice>}
            <div className="conversation-composer">
              <button
                type="button"
                aria-label="Attach a financial document"
                onClick={() =>
                  setNotice(
                    "Attachments and document intelligence are not enabled. No file was selected or uploaded.",
                  )
                }
              >
                <Icon name="attachment" />
              </button>
              <textarea
                value={draft}
                onChange={(event) => setDraft(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === "Enter" && !event.shiftKey) {
                    event.preventDefault();
                    submit();
                  }
                }}
                aria-label="Message Chatbooks"
                placeholder="Describe what you want to do…"
                rows={1}
              />
              <button
                type="button"
                aria-label="Preview unavailable message"
                disabled={!draft.trim()}
                onClick={submit}
              >
                <Icon name="send" />
              </button>
            </div>
            <p>Enter to preview · Shift + Enter for a new line · Nothing is sent or posted</p>
          </div>
        </section>

        <aside className="review-rail" aria-label="Proposal review status">
          <div className="review-rail-heading">
            <span className="review-lock" aria-hidden="true">
              <Icon name="shield" />
            </span>
            <div>
              <p className="eyebrow">Review before money moves</p>
              <h2>No proposal to review</h2>
            </div>
          </div>
          <p>
            A future conversational request will appear here only after it becomes a structured
            proposal. No conversation can confirm or post it automatically.
          </p>
          <ol className="review-steps">
            <li>
              <span>1</span>
              <div>
                <strong>Proposal</strong>
                <small>Exact date, amount, accounts, and context</small>
              </div>
            </li>
            <li>
              <span>2</span>
              <div>
                <strong>Validation</strong>
                <small>Deterministic accounting checks</small>
              </div>
            </li>
            <li>
              <span>3</span>
              <div>
                <strong>Your confirmation</strong>
                <small>Bound to the exact reviewed version</small>
              </div>
            </li>
            <li>
              <span>4</span>
              <div>
                <strong>Posting</strong>
                <small>Audited through the accounting engine</small>
              </div>
            </li>
          </ol>
          {spaceKind === "business" ? (
            <Link href="/money/proposals/new" className="review-manual-link">
              Open the manual proposal flow <Icon name="arrow" />
            </Link>
          ) : (
            <Notice>Personal proposal creation remains unavailable.</Notice>
          )}
        </aside>
      </div>
    </div>
  );
}
