import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { AppShell } from "@/components/app-shell";
import { Modal, Tabs } from "@/components/ui";
import { ChatWorkspace } from "@/features/chat/chat-workspace";
import { PersonalDeferred } from "@/features/context/personal-deferred";

const shell = vi.hoisted(() => ({
  pathname: "/chat",
  spaceKind: "business" as "business" | "personal",
}));

vi.mock("next/navigation", () => ({
  usePathname: () => shell.pathname,
  useRouter: () => ({ replace: vi.fn() }),
}));

vi.mock("@/features/auth/auth-provider", () => ({
  useAuth: () => ({
    user: { id: "user-1", name: "Sam", username: "sam" },
    logout: vi.fn(),
  }),
}));

vi.mock("@/features/context/context-switcher", () => ({
  ContextSwitcher: () => <button type="button">Business space</button>,
}));

vi.mock("@/features/context/financial-space-provider", () => ({
  useFinancialSpace: () => ({
    space:
      shell.spaceKind === "personal"
        ? { kind: "personal" }
        : { kind: "business", organizationId: "org-1" },
    organization:
      shell.spaceKind === "business"
        ? {
            id: "org-1",
            name: "North Studio",
            currency: "BDT",
            minor_unit_digits: 2,
            role: "ACCOUNTANT",
          }
        : null,
    loading: false,
    error: null,
    reloadOrganizations: vi.fn(),
  }),
}));

describe("M5.2-UI0 product shell", () => {
  beforeEach(() => {
    shell.pathname = "/chat";
    shell.spaceKind = "business";
  });

  it("uses the product navigation order and includes Settings", () => {
    render(
      <AppShell>
        <p>Chat workspace</p>
      </AppShell>,
    );
    const sidebar = document.querySelector(".sidebar");
    expect(sidebar).not.toBeNull();
    const links = within(sidebar as HTMLElement)
      .getAllByRole("link")
      .filter((link) => link.closest("nav"))
      .map((link) => link.textContent?.trim());
    expect(links).toEqual(["Chat", "Money", "Activity", "Reports", "Projects", "Settings"]);
  });

  it("keeps Chat visible in Personal context and fails closed on Personal Money", () => {
    shell.spaceKind = "personal";
    const { rerender } = render(
      <AppShell>
        <p>Personal chat shell</p>
      </AppShell>,
    );
    expect(screen.getByText("Personal chat shell")).toBeInTheDocument();
    expect(document.querySelector('.sidebar a[href="/projects"]')).toBeNull();

    shell.pathname = "/money";
    rerender(
      <AppShell>
        <p>Private financial data</p>
      </AppShell>,
    );
    expect(screen.getByText("Personal finance is coming later")).toBeInTheDocument();
    expect(screen.queryByText("Private financial data")).not.toBeInTheDocument();
    expect(screen.getByText(/operations are not enabled/i)).toBeInTheDocument();
  });
});

describe("conversation and review foundation", () => {
  it("keeps draft messages local and states that no financial action occurred", async () => {
    const user = userEvent.setup();
    render(<ChatWorkspace spaceKind="personal" spaceName="Personal" />);
    expect(screen.getByText("AI actions unavailable")).toBeInTheDocument();
    expect(screen.getByText("No proposal to review")).toBeInTheDocument();
    await user.type(screen.getByRole("textbox", { name: "Message Chatbooks" }), "I spent money");
    await user.click(screen.getByRole("button", { name: "Preview unavailable message" }));
    expect(screen.getByText("I spent money")).toBeInTheDocument();
    expect(screen.getByText("You · not sent")).toBeInTheDocument();
    expect(screen.getByText(/nothing was sent or changed/i)).toBeInTheDocument();
    expect(screen.getByText(/Personal proposal creation remains unavailable/i)).toBeInTheDocument();
  });

  it("discloses that attachments are unavailable", async () => {
    const user = userEvent.setup();
    render(<ChatWorkspace spaceKind="business" spaceName="North Studio" />);
    await user.click(screen.getByRole("button", { name: "Attach a financial document" }));
    expect(screen.getByText(/No file was selected or uploaded/i)).toBeInTheDocument();
  });
});

describe("accessible interaction primitives", () => {
  function TabHarness() {
    const [value, setValue] = useState<"money" | "reports">("money");
    return (
      <Tabs
        label="Example views"
        value={value}
        options={[
          { id: "money", label: "Money" },
          { id: "reports", label: "Reports" },
        ]}
        onChange={setValue}
      />
    );
  }

  it("moves through tabs with arrow keys", async () => {
    const user = userEvent.setup();
    render(<TabHarness />);
    const money = screen.getByRole("tab", { name: "Money" });
    money.focus();
    await user.keyboard("{ArrowRight}");
    expect(screen.getByRole("tab", { name: "Reports" })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByRole("tab", { name: "Reports" })).toHaveFocus();
  });

  it("closes a review dialog with Escape and restores focus", async () => {
    const user = userEvent.setup();
    function ModalHarness() {
      const [open, setOpen] = useState(false);
      return (
        <>
          <button type="button" onClick={() => setOpen(true)}>
            Open review
          </button>
          <Modal open={open} title="Confirm exact proposal" onClose={() => setOpen(false)}>
            <button type="button">Confirm</button>
          </Modal>
        </>
      );
    }
    render(<ModalHarness />);
    const trigger = screen.getByRole("button", { name: "Open review" });
    await user.click(trigger);
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    await user.keyboard("{Escape}");
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(trigger).toHaveFocus();
  });

  it("uses an explicit business-only Personal Projects state", () => {
    render(<PersonalDeferred section="Projects" />);
    expect(screen.getByText("Projects are business-only")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Return to Chat" })).toHaveAttribute("href", "/chat");
  });
});
