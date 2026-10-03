"use client";

import { ChatWorkspace } from "@/features/chat/chat-workspace";
import { useFinancialSpace } from "@/features/context/financial-space-provider";

export default function ChatPage() {
  const { space, organization } = useFinancialSpace();
  return (
    <ChatWorkspace
      spaceKind={space.kind}
      spaceName={space.kind === "personal" ? "Personal" : (organization?.name ?? "Business")}
    />
  );
}
