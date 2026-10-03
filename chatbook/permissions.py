"""Explicit organization-role permissions for the HTTP application boundary."""

from enum import StrEnum

from .domain import OrganizationRole


class Permission(StrEnum):
    VIEW = "view"
    CREATE_PROPOSALS = "create_proposals"
    CONFIRM_PROPOSALS = "confirm_proposals"
    CREATE_MANUAL_JOURNALS = "create_manual_journals"
    REVERSE_ENTRIES = "reverse_entries"
    VIEW_REPORTS = "view_reports"
    VIEW_AUDIT = "view_audit"
    LOCK_PERIODS = "lock_periods"
    MANAGE_ACCOUNTS = "manage_accounts"
    MANAGE_PROJECTS = "manage_projects"
    MANAGE_PERIODS = "manage_periods"
    MANAGE_MEMBERS = "manage_members"


ROLE_PERMISSIONS: dict[OrganizationRole, frozenset[Permission]] = {
    OrganizationRole.VIEWER: frozenset({Permission.VIEW, Permission.VIEW_REPORTS}),
    OrganizationRole.MEMBER: frozenset(
        {
            Permission.VIEW,
            Permission.CREATE_PROPOSALS,
            Permission.MANAGE_PROJECTS,
            Permission.VIEW_REPORTS,
        }
    ),
    OrganizationRole.ACCOUNTANT: frozenset(
        {
            Permission.VIEW,
            Permission.CREATE_PROPOSALS,
            Permission.CONFIRM_PROPOSALS,
            Permission.CREATE_MANUAL_JOURNALS,
            Permission.REVERSE_ENTRIES,
            Permission.VIEW_REPORTS,
            Permission.VIEW_AUDIT,
            Permission.MANAGE_ACCOUNTS,
            Permission.MANAGE_PROJECTS,
            Permission.MANAGE_PERIODS,
        }
    ),
    OrganizationRole.ADMIN: frozenset(Permission),
    OrganizationRole.OWNER: frozenset(Permission),
}


def role_allows(role: OrganizationRole, permission: Permission) -> bool:
    return permission in ROLE_PERMISSIONS[role]
