"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { useAuth } from "@/features/auth/auth-provider";
import { BusinessOnboarding } from "@/features/context/business-onboarding";
import { ContextSwitcher } from "@/features/context/context-switcher";
import { useFinancialSpace } from "@/features/context/financial-space-provider";
import { PersonalDeferred } from "@/features/context/personal-deferred";

import { Icon, type IconName } from "./icons";
import { CompanionMark } from "./money-companion";
import { ErrorState, LoadingState } from "./ui";

const navigation: Array<{ href: string; label: string; icon: IconName; businessOnly?: boolean }> = [
  { href: "/chat", label: "Chat", icon: "chat" },
  { href: "/money", label: "Money", icon: "money" },
  { href: "/activity", label: "Activity", icon: "activity" },
  { href: "/reports", label: "Reports", icon: "reports" },
  { href: "/projects", label: "Projects", icon: "projects", businessOnly: true },
  { href: "/settings", label: "Settings", icon: "settings" },
];

const mobilePrimaryPaths = new Set(["/chat", "/money", "/activity", "/reports"]);

function personalSection(
  pathname: string,
): "Money" | "Activity" | "Reports" | "Projects" | "Settings" | null {
  if (pathname.startsWith("/money")) return "Money";
  if (pathname.startsWith("/activity")) return "Activity";
  if (pathname.startsWith("/reports")) return "Reports";
  if (pathname.startsWith("/projects")) return "Projects";
  if (pathname.startsWith("/settings")) return "Settings";
  return null;
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { user, logout } = useAuth();
  const { space, organization, loading, error, reloadOrganizations } = useFinancialSpace();
  const [profileOpen, setProfileOpen] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const visibleNavigation = navigation.filter(
    (item) => !item.businessOnly || space.kind === "business",
  );
  const mobilePrimary = visibleNavigation.filter((item) => mobilePrimaryPaths.has(item.href));
  const mobileSecondary = visibleNavigation.filter((item) => !mobilePrimaryPaths.has(item.href));
  const deferredSection = space.kind === "personal" ? personalSection(pathname) : null;

  useEffect(() => {
    if (!mobileMenuOpen) return;
    function closeWithEscape(event: KeyboardEvent) {
      if (event.key === "Escape") setMobileMenuOpen(false);
    }
    document.addEventListener("keydown", closeWithEscape);
    return () => document.removeEventListener("keydown", closeWithEscape);
  }, [mobileMenuOpen]);

  async function signOut() {
    await logout();
    router.replace("/login");
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <Link href="/chat" className="brand" aria-label="Chatbooks home">
          <CompanionMark />
          <span>
            <strong>Chatbooks</strong>
            <small>Money, made clearer</small>
          </span>
        </Link>
        <ContextSwitcher />
        <nav aria-label="Primary navigation">
          {visibleNavigation.map((item) => {
            const active = pathname === item.href || pathname.startsWith(`${item.href}/`);
            return (
              <Link
                key={item.href}
                href={item.href}
                className={active ? "active" : undefined}
                aria-current={active ? "page" : undefined}
              >
                <Icon name={item.icon} />
                <span>{item.label}</span>
              </Link>
            );
          })}
        </nav>
        <div className="sidebar-coach" aria-hidden="true">
          <CompanionMark />
          <span>
            <strong>Small steps. Clear books.</strong>
            <small>Every financial change waits for review.</small>
          </span>
        </div>
        <div className="sidebar-foot">
          <button
            className="profile-trigger"
            onClick={() => setProfileOpen((value) => !value)}
            aria-expanded={profileOpen}
          >
            <span className="avatar">{user?.name.slice(0, 1).toUpperCase()}</span>
            <span>
              <strong>{user?.name}</strong>
              <small>{organization?.role.toLowerCase() ?? "personal"}</small>
            </span>
            <Icon name="chevron" />
          </button>
          {profileOpen && (
            <div className="profile-menu">
              <p>{user?.username}</p>
              <button onClick={() => void signOut()}>Log out</button>
            </div>
          )}
        </div>
      </aside>
      <header className="mobile-header">
        <Link href="/chat" className="brand">
          <CompanionMark />
          <strong>Chatbooks</strong>
        </Link>
        <ContextSwitcher />
      </header>
      <main className="app-main">
        {loading ? (
          <LoadingState label="Loading your financial context" />
        ) : error ? (
          <ErrorState error={error} onRetry={() => void reloadOrganizations()} />
        ) : deferredSection ? (
          <PersonalDeferred section={deferredSection} />
        ) : organization === null ? (
          space.kind === "business" ? (
            <BusinessOnboarding />
          ) : (
            children
          )
        ) : (
          children
        )}
      </main>
      <nav className="mobile-nav" aria-label="Mobile navigation">
        {mobilePrimary.map((item) => {
          const active = pathname === item.href || pathname.startsWith(`${item.href}/`);
          return (
            <Link
              key={item.href}
              href={item.href}
              className={active ? "active" : undefined}
              aria-current={active ? "page" : undefined}
            >
              <Icon name={item.icon} />
              <span>{item.label}</span>
            </Link>
          );
        })}
        <button
          type="button"
          className={mobileSecondary.some((item) => pathname.startsWith(item.href)) ? "active" : ""}
          aria-haspopup="menu"
          aria-expanded={mobileMenuOpen}
          onClick={() => setMobileMenuOpen((value) => !value)}
        >
          <Icon name="more" />
          <span>More</span>
        </button>
      </nav>
      {mobileMenuOpen && (
        <div className="mobile-more-backdrop" onMouseDown={() => setMobileMenuOpen(false)}>
          <div
            className="mobile-more-menu"
            role="menu"
            aria-label="More destinations"
            onMouseDown={(event) => event.stopPropagation()}
          >
            <div>
              <strong>More</strong>
              <button
                type="button"
                className="icon-button"
                aria-label="Close more destinations"
                onClick={() => setMobileMenuOpen(false)}
              >
                <Icon name="close" />
              </button>
            </div>
            {mobileSecondary.map((item) => {
              const active = pathname === item.href || pathname.startsWith(`${item.href}/`);
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  role="menuitem"
                  className={active ? "active" : undefined}
                  onClick={() => setMobileMenuOpen(false)}
                >
                  <Icon name={item.icon} />
                  <span>{item.label}</span>
                  <Icon name="arrow" />
                </Link>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
