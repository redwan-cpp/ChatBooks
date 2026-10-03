"""Typed HTTP request and response contracts."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StrictInt, model_validator

from ..domain import AccountType, OrganizationRole, ProjectStatus

MinorUnits = Annotated[StrictInt, Field(ge=0, le=9_000_000_000_000)]


class ApiModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ErrorResponse(ApiModel):
    error: str
    message: str
    request_id: str
    details: object | None = None


class Page[PageItem](ApiModel):
    items: list[PageItem]
    total: int
    offset: int
    limit: int


class UserResponse(ApiModel):
    id: str
    name: str
    username: str


class RegisterRequest(ApiModel):
    name: str = Field(min_length=1, max_length=200)
    username: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=12, max_length=1024)


class LoginRequest(ApiModel):
    username: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=1024)


class TokenResponse(ApiModel):
    access_token: str
    token_type: Literal["bearer"]
    expires_at: str
    user: UserResponse


class OrganizationCreate(ApiModel):
    name: str = Field(min_length=1, max_length=200)
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    minor_unit_digits: StrictInt = Field(ge=0, le=6)


class OrganizationResponse(ApiModel):
    id: str
    name: str
    currency: str
    minor_unit_digits: int
    role: OrganizationRole


class MembershipCreate(ApiModel):
    user_id: str
    role: OrganizationRole = OrganizationRole.MEMBER


class MembershipResponse(ApiModel):
    user_id: str
    name: str
    role: OrganizationRole


class ProjectCreate(ApiModel):
    name: str = Field(min_length=1, max_length=200)
    description: str = ""
    client: str | None = None
    expected_revenue: MinorUnits | None = None
    budget: MinorUnits | None = None
    starts_on: str | None = None
    ends_on: str | None = None
    status: ProjectStatus = ProjectStatus.PLANNED


class ProjectUpdate(ApiModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    client: str | None = None
    expected_revenue: MinorUnits | None = None
    budget: MinorUnits | None = None
    starts_on: str | None = None
    ends_on: str | None = None
    status: ProjectStatus | None = None

    @model_validator(mode="after")
    def require_change(self) -> "ProjectUpdate":
        if not self.model_fields_set:
            raise ValueError("At least one project field is required.")
        for field in ("name", "description", "status"):
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"{field} cannot be null.")
        return self


class ProjectResponse(ApiModel):
    id: str
    organization_id: str
    name: str
    description: str
    client: str | None
    expected_revenue: int | None
    budget: int | None
    starts_on: str | None
    ends_on: str | None
    status: ProjectStatus


class AccountCreate(ApiModel):
    code: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=200)
    account_type: AccountType


class AccountUpdate(ApiModel):
    active: bool


class AccountResponse(ApiModel):
    id: str
    organization_id: str
    code: str
    name: str
    account_type: AccountType
    active: bool


class PeriodCreate(ApiModel):
    name: str = Field(min_length=1, max_length=200)
    starts_on: str
    ends_on: str


class PeriodResponse(ApiModel):
    id: str
    organization_id: str
    name: str
    starts_on: str
    ends_on: str
    locked: bool


class ProposalLineRequest(ApiModel):
    account_id: str
    debit: MinorUnits = 0
    credit: MinorUnits = 0
    project_id: str | None = None


class ProposalCreate(ApiModel):
    entry_date: str
    description: str = Field(min_length=1)
    document_id: str | None = None
    lines: list[ProposalLineRequest] = Field(max_length=1000)


class ProposalLineResponse(ApiModel):
    position: int
    account_id: str
    code: str
    name: str
    debit: int
    credit: int
    project_id: str | None


class ProposalResponse(ApiModel):
    id: str
    organization_id: str
    entry_date: str
    description: str
    document_id: str | None
    reverses_entry_id: str | None
    version: int
    state: str
    lines: list[ProposalLineResponse]
    posted_entry_id: str | None
    status: str
    lifecycle_state: Literal["PROPOSED", "VALIDATED", "CONFIRMED", "POSTED"]
    currency: str
    minor_unit_digits: int


class ValidationResponse(ApiModel):
    id: str
    transaction_id: str
    fingerprint: str
    debit_total: int
    credit_total: int


class ConfirmationRequest(ApiModel):
    validation_id: str
    proposal_version: StrictInt = Field(ge=1)
    accepted: Literal[True]


class ConfirmationResponse(ApiModel):
    id: str
    validation_id: str
    actor_id: str
    proposal_id: str
    proposal_version: int
    confirmed_at: str
    confirmation_request_id: str


class PostRequest(ApiModel):
    confirmation_id: str


class PostResponse(ApiModel):
    entry_id: str


class ReversalRequest(ApiModel):
    entry_date: str
    reason: str = Field(min_length=1)


class JournalLineResponse(ApiModel):
    position: int
    account_id: str
    code: str
    account_name: str
    account_type: AccountType
    debit: int
    credit: int
    project_id: str | None


class JournalEntryResponse(ApiModel):
    id: str
    organization_id: str
    transaction_id: str
    confirmation_id: str
    period_id: str
    entry_date: str
    description: str
    reverses_entry_id: str | None
    state: Literal["posted"]
    lines: list[JournalLineResponse]
    debit_total: int
    credit_total: int
    line_count: int
    project_ids: list[str]


class JournalEntrySummaryResponse(ApiModel):
    id: str
    organization_id: str
    transaction_id: str
    confirmation_id: str
    period_id: str
    entry_date: str
    description: str
    reverses_entry_id: str | None
    state: Literal["posted"]
    debit_total: int
    credit_total: int
    line_count: int
    project_ids: list[str]


class LedgerLineResponse(ApiModel):
    entry_id: str
    transaction_id: str
    entry_date: str
    description: str
    reverses_entry_id: str | None
    line_id: str
    position: int
    account_id: str
    code: str
    account_name: str
    account_type: AccountType
    debit: int
    credit: int
    project_id: str | None


class BalanceResponse(ApiModel):
    account_id: str
    code: str
    name: str
    account_type: AccountType
    debits: int
    credits: int
    net_debit: int
    debit_balance: int
    credit_balance: int


class TrialBalanceResponse(ApiModel):
    currency: str
    minor_unit_digits: int
    as_of: str | None
    project_id: str | None
    accounts: list[BalanceResponse]
    total_debits: int
    total_credits: int
    balanced: bool


class IncomeStatementResponse(ApiModel):
    currency: str
    minor_unit_digits: int
    starts_on: str
    ends_on: str
    revenue: int
    expenses: int
    net_income: int


class BalanceSheetResponse(ApiModel):
    currency: str
    minor_unit_digits: int
    as_of: str
    assets: int
    liabilities: int
    recorded_equity: int
    unclosed_earnings: int
    total_equity: int
    balanced: bool


class CashFlowResponse(ApiModel):
    currency: str
    minor_unit_digits: int
    starts_on: str
    ends_on: str
    cash_accounts: list[AccountResponse]
    movements: list[LedgerLineResponse]
    total_inflows: int
    total_outflows: int
    net_change: int
    classification: Literal["unclassified_cash_movements"]


class AuditEventResponse(ApiModel):
    sequence: int
    organization_id: str
    actor_id: str
    occurred_at: str
    event_type: str
    entity_type: str
    entity_id: str
    previous_state: dict[str, object] | None
    new_state: dict[str, object] | None
    metadata: dict[str, object]
