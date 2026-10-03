import type { OrganizationRole } from "@/lib/api/types";

export type UiPermission =
  | "create_proposal"
  | "confirm_proposal"
  | "post_journal"
  | "reverse_entry"
  | "manage_project"
  | "manage_account"
  | "manage_period"
  | "lock_period"
  | "view_audit";

const all: readonly UiPermission[] = [
  "create_proposal",
  "confirm_proposal",
  "post_journal",
  "reverse_entry",
  "manage_project",
  "manage_account",
  "manage_period",
  "lock_period",
  "view_audit",
];

const permissions: Record<OrganizationRole, ReadonlySet<UiPermission>> = {
  OWNER: new Set(all),
  ADMIN: new Set(all),
  ACCOUNTANT: new Set([
    "create_proposal",
    "confirm_proposal",
    "post_journal",
    "reverse_entry",
    "manage_project",
    "manage_account",
    "manage_period",
    "view_audit",
  ]),
  MEMBER: new Set(["create_proposal", "manage_project"]),
  VIEWER: new Set(),
};

export function allows(role: OrganizationRole | undefined, permission: UiPermission): boolean {
  return role ? permissions[role].has(permission) : false;
}
