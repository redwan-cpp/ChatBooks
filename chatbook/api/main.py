"""Thin FastAPI boundary over authenticated application and accounting services."""

import asyncio
import hashlib
import json
import logging
import os
import threading
import time
from collections.abc import AsyncIterator, Callable, Generator, Sequence
from contextlib import asynccontextmanager
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Annotated, Any, cast
from uuid import uuid4

import uvicorn
from fastapi import APIRouter, Depends, FastAPI, Header, Query, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from ..auth import AuthenticatedUser, AuthService
from ..domain import ChatbookError, LineInput, OrganizationRole, ProjectStatus, TrialBalance
from ..engine import AccountingEngine
from ..maintenance import (
    MaintenanceGate,
    MaintenanceMiddleware,
    MaintenancePaths,
    shutdown_requested,
)
from ..permissions import Permission, role_allows
from ..runtime import RuntimeConfiguration
from .schemas import (
    AccountCreate,
    AccountResponse,
    AccountUpdate,
    AuditEventResponse,
    BalanceSheetResponse,
    CashFlowResponse,
    ConfirmationRequest,
    ConfirmationResponse,
    IncomeStatementResponse,
    JournalEntryResponse,
    JournalEntrySummaryResponse,
    LedgerLineResponse,
    LoginRequest,
    MembershipCreate,
    MembershipResponse,
    OrganizationCreate,
    OrganizationResponse,
    Page,
    PeriodCreate,
    PeriodResponse,
    PostRequest,
    PostResponse,
    ProjectCreate,
    ProjectResponse,
    ProjectUpdate,
    ProposalCreate,
    ProposalResponse,
    RegisterRequest,
    ReversalRequest,
    TokenResponse,
    TrialBalanceResponse,
    UserResponse,
    ValidationResponse,
)

logger = logging.getLogger("chatbook.api")
bearer = HTTPBearer(auto_error=False)
router = APIRouter(prefix="/api/v1")
OPERATIONAL_EVENT_LOG_ENV = "CHATBOOK_OPERATIONAL_EVENT_LOG_PATH"


@dataclass(frozen=True, slots=True)
class RequestIdentity:
    user: AuthenticatedUser
    token: str


class OperationalEventSink:
    """Append sanitized structured events without changing request or ledger semantics."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path).resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def emit(self, event: dict[str, object]) -> None:
        encoded = json.dumps(event, sort_keys=True, separators=(",", ":")) + "\n"
        with self._lock, self.path.open("a", encoding="utf-8") as stream:
            stream.write(encoded)


def _emit_operational_event(request: Request, event: dict[str, object]) -> None:
    sink = cast(OperationalEventSink | None, request.app.state.operational_event_sink)
    if sink is None:
        return
    try:
        sink.emit(event)
    except OSError:
        logger.exception("Operational event sink failed")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        supplied = request.headers.get("X-Request-ID", "")
        request_id = supplied if 1 <= len(supplied) <= 200 else str(uuid4())
        request.state.request_id = request_id
        started = time.perf_counter()
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        event: dict[str, object] = {
            "event": "http_request",
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status": response.status_code,
            "duration_ms": round((time.perf_counter() - started) * 1000, 3),
        }
        logger.info(json.dumps(event, separators=(",", ":")))
        _emit_operational_event(request, event)
        return response


def _request_id(request: Request) -> str:
    return str(getattr(request.state, "request_id", "unknown"))


def _status_for_error(code: str) -> int:
    if code in {"authentication_required", "invalid_credentials"}:
        return status.HTTP_401_UNAUTHORIZED
    if code in {"forbidden", "confirmation_actor"}:
        return status.HTTP_403_FORBIDDEN
    if code == "not_found":
        return status.HTTP_404_NOT_FOUND
    if code in {
        "already_posted",
        "already_reversed",
        "constraint_violation",
        "idempotency_conflict",
        "period_locked",
        "stale_proposal_version",
        "stale_validation",
        "username_taken",
    }:
        return status.HTTP_409_CONFLICT
    return status.HTTP_422_UNPROCESSABLE_CONTENT


async def _chatbook_error_handler(request: Request, exc: Exception) -> JSONResponse:
    error = cast(ChatbookError, exc)
    response_status = _status_for_error(error.code)
    headers = {"WWW-Authenticate": "Bearer"} if response_status == 401 else None
    logger.warning(
        json.dumps(
            {
                "event": "chatbook_error",
                "request_id": _request_id(request),
                "path": request.url.path,
                "status": response_status,
                "error": error.code,
            },
            separators=(",", ":"),
        )
    )
    _emit_operational_event(
        request,
        {
            "event": "chatbook_error",
            "request_id": _request_id(request),
            "path": request.url.path,
            "status": response_status,
            "error": error.code,
        },
    )
    return JSONResponse(
        status_code=response_status,
        content={
            "error": error.code,
            "message": str(error),
            "request_id": _request_id(request),
            "details": None,
        },
        headers=headers,
    )


async def _http_error_handler(request: Request, exc: Exception) -> JSONResponse:
    error = cast(StarletteHTTPException, exc)
    return JSONResponse(
        status_code=error.status_code,
        content={
            "error": "http_error",
            "message": str(error.detail),
            "request_id": _request_id(request),
            "details": None,
        },
        headers=error.headers,
    )


async def _validation_error_handler(request: Request, exc: Exception) -> JSONResponse:
    error = cast(RequestValidationError, exc)
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content={
            "error": "invalid_request",
            "message": "Request validation failed.",
            "request_id": _request_id(request),
            "details": json.loads(json.dumps(error.errors(), default=str)),
        },
    )


async def _unexpected_error_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled API error", exc_info=exc)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "internal_error",
            "message": "The request could not be completed.",
            "request_id": _request_id(request),
            "details": None,
        },
    )


def _database_path(request: Request) -> str:
    return cast(str, request.app.state.database_path)


def get_engine(request: Request) -> Generator[AccountingEngine]:
    engine = (
        AccountingEngine.for_canonical_rehearsal(_database_path(request), allow_thread_handoff=True)
        if cast(bool, request.app.state.canonical_rehearsal)
        else AccountingEngine.for_runtime(
            cast(RuntimeConfiguration, request.app.state.runtime_configuration),
            allow_thread_handoff=True,
        )
    )
    try:
        yield engine
    finally:
        engine.close()


def get_auth_service(request: Request) -> Generator[AuthService]:
    rehearsal = cast(bool, request.app.state.canonical_rehearsal)
    service = AuthService(
        _database_path(request),
        session_ttl_seconds=cast(int, request.app.state.session_ttl_seconds),
        canonical_rehearsal=rehearsal,
        runtime_configuration=(
            None
            if rehearsal
            else cast(RuntimeConfiguration, request.app.state.runtime_configuration)
        ),
        allow_thread_handoff=True,
    )
    try:
        yield service
    finally:
        service.close()


EngineDep = Annotated[AccountingEngine, Depends(get_engine)]
AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
BearerDep = Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)]


def get_identity(credentials: BearerDep, auth: AuthServiceDep) -> RequestIdentity:
    if credentials is None or credentials.scheme.casefold() != "bearer":
        raise ChatbookError("authentication_required", "A valid bearer token is required.")
    return RequestIdentity(auth.authenticate(credentials.credentials), credentials.credentials)


IdentityDep = Annotated[RequestIdentity, Depends(get_identity)]


def require_permission(
    permission: Permission,
) -> Callable[[str, RequestIdentity, AccountingEngine], OrganizationRole]:
    def dependency(
        organization_id: str,
        identity: IdentityDep,
        engine: EngineDep,
    ) -> OrganizationRole:
        role = engine.membership_role(identity.user.id, organization_id)
        if not role_allows(role, permission):
            raise ChatbookError("forbidden", "Your organization role does not allow this action.")
        return role

    return dependency


ViewRole = Annotated[OrganizationRole, Depends(require_permission(Permission.VIEW))]
ProposalRole = Annotated[OrganizationRole, Depends(require_permission(Permission.CREATE_PROPOSALS))]
ConfirmRole = Annotated[OrganizationRole, Depends(require_permission(Permission.CONFIRM_PROPOSALS))]
PostRole = Annotated[
    OrganizationRole, Depends(require_permission(Permission.CREATE_MANUAL_JOURNALS))
]
ReversalRole = Annotated[OrganizationRole, Depends(require_permission(Permission.REVERSE_ENTRIES))]
ReportRole = Annotated[OrganizationRole, Depends(require_permission(Permission.VIEW_REPORTS))]
AuditRole = Annotated[OrganizationRole, Depends(require_permission(Permission.VIEW_AUDIT))]
LockRole = Annotated[OrganizationRole, Depends(require_permission(Permission.LOCK_PERIODS))]
AccountRole = Annotated[OrganizationRole, Depends(require_permission(Permission.MANAGE_ACCOUNTS))]
ProjectRole = Annotated[OrganizationRole, Depends(require_permission(Permission.MANAGE_PROJECTS))]
PeriodRole = Annotated[OrganizationRole, Depends(require_permission(Permission.MANAGE_PERIODS))]
MemberRole = Annotated[OrganizationRole, Depends(require_permission(Permission.MANAGE_MEMBERS))]

Offset = Annotated[int, Query(ge=0)]
Limit = Annotated[int, Query(ge=1, le=100)]
IdempotencyKey = Annotated[str, Header(alias="Idempotency-Key", min_length=8, max_length=200)]


def _page(items: Sequence[Any], offset: int, limit: int) -> dict[str, object]:
    return {
        "items": list(items[offset : offset + limit]),
        "total": len(items),
        "offset": offset,
        "limit": limit,
    }


def _fingerprint(payload: dict[str, object]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _trial_response(report: TrialBalance) -> dict[str, object]:
    accounts = [
        {
            **asdict(account),
            "net_debit": account.net_debit,
            "debit_balance": account.debit_balance,
            "credit_balance": account.credit_balance,
        }
        for account in report.accounts
    ]
    return {
        "currency": report.currency,
        "minor_unit_digits": report.minor_unit_digits,
        "as_of": report.as_of,
        "project_id": report.project_id,
        "accounts": accounts,
        "total_debits": report.total_debits,
        "total_credits": report.total_credits,
        "balanced": report.balanced,
    }


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/auth/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, auth: AuthServiceDep) -> AuthenticatedUser:
    return auth.register(payload.name, payload.username, payload.password)


@router.post("/auth/token", response_model=TokenResponse)
def login(payload: LoginRequest, auth: AuthServiceDep) -> dict[str, object]:
    session = auth.login(payload.username, payload.password)
    return {
        "access_token": session.access_token,
        "token_type": session.token_type,
        "expires_at": session.expires_at,
        "user": asdict(session.user),
    }


@router.get("/auth/me", response_model=UserResponse)
def me(identity: IdentityDep) -> AuthenticatedUser:
    return identity.user


@router.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(identity: IdentityDep, auth: AuthServiceDep) -> Response:
    auth.logout(identity.token)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/organizations", response_model=list[OrganizationResponse])
def list_organizations(identity: IdentityDep, engine: EngineDep) -> tuple[dict[str, object], ...]:
    return engine.organizations_for_actor(identity.user.id)


@router.post(
    "/organizations", response_model=OrganizationResponse, status_code=status.HTTP_201_CREATED
)
def create_organization(
    payload: OrganizationCreate, identity: IdentityDep, engine: EngineDep
) -> dict[str, object]:
    organization_id = engine.create_organization(
        identity.user.id, payload.name, payload.currency, payload.minor_unit_digits
    )
    return engine.get_organization(identity.user.id, organization_id)


@router.get("/organizations/{organization_id}", response_model=OrganizationResponse)
def get_organization(
    organization_id: str, identity: IdentityDep, engine: EngineDep, _role: ViewRole
) -> dict[str, object]:
    return engine.get_organization(identity.user.id, organization_id)


@router.get("/organizations/{organization_id}/members", response_model=list[MembershipResponse])
def list_members(
    organization_id: str, identity: IdentityDep, engine: EngineDep, _role: MemberRole
) -> tuple[dict[str, object], ...]:
    return engine.list_members(identity.user.id, organization_id)


@router.post(
    "/organizations/{organization_id}/members",
    response_model=MembershipResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_member(
    organization_id: str,
    payload: MembershipCreate,
    identity: IdentityDep,
    engine: EngineDep,
    role: MemberRole,
) -> dict[str, object]:
    if payload.role is OrganizationRole.OWNER and role is not OrganizationRole.OWNER:
        raise ChatbookError("forbidden", "Only an owner may add another owner.")
    engine.add_member(identity.user.id, organization_id, payload.user_id, payload.role)
    return next(
        member
        for member in engine.list_members(identity.user.id, organization_id)
        if member["user_id"] == payload.user_id
    )


@router.get("/organizations/{organization_id}/projects", response_model=Page[ProjectResponse])
def list_projects(
    organization_id: str,
    identity: IdentityDep,
    engine: EngineDep,
    _role: ViewRole,
    offset: Offset = 0,
    limit: Limit = 50,
) -> dict[str, object]:
    return _page(engine.list_projects(identity.user.id, organization_id), offset, limit)


@router.post(
    "/organizations/{organization_id}/projects",
    response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_project(
    organization_id: str,
    payload: ProjectCreate,
    identity: IdentityDep,
    engine: EngineDep,
    _role: ProjectRole,
) -> dict[str, object]:
    project_id = engine.create_project(
        identity.user.id,
        organization_id,
        payload.name,
        description=payload.description,
        client=payload.client,
        expected_revenue=payload.expected_revenue,
        budget=payload.budget,
        starts_on=payload.starts_on,
        ends_on=payload.ends_on,
        status=payload.status,
    )
    return engine.get_project(identity.user.id, organization_id, project_id)


@router.get(
    "/organizations/{organization_id}/projects/{project_id}", response_model=ProjectResponse
)
def get_project(
    organization_id: str,
    project_id: str,
    identity: IdentityDep,
    engine: EngineDep,
    _role: ViewRole,
) -> dict[str, object]:
    return engine.get_project(identity.user.id, organization_id, project_id)


@router.patch(
    "/organizations/{organization_id}/projects/{project_id}", response_model=ProjectResponse
)
def update_project(
    organization_id: str,
    project_id: str,
    payload: ProjectUpdate,
    identity: IdentityDep,
    engine: EngineDep,
    _role: ProjectRole,
) -> dict[str, object]:
    current = engine.get_project(identity.user.id, organization_id, project_id)
    changes = payload.model_dump(exclude_unset=True)
    merged = {**current, **changes}
    return engine.update_project(
        identity.user.id,
        organization_id,
        project_id,
        name=cast(str, merged["name"]),
        description=cast(str, merged["description"]),
        client=cast(str | None, merged["client"]),
        expected_revenue=cast(int | None, merged["expected_revenue"]),
        budget=cast(int | None, merged["budget"]),
        starts_on=cast(str | None, merged["starts_on"]),
        ends_on=cast(str | None, merged["ends_on"]),
        status=ProjectStatus(str(merged["status"])),
    )


@router.get("/organizations/{organization_id}/accounts", response_model=Page[AccountResponse])
def list_accounts(
    organization_id: str,
    identity: IdentityDep,
    engine: EngineDep,
    _role: ViewRole,
    offset: Offset = 0,
    limit: Limit = 50,
) -> dict[str, object]:
    return _page(engine.list_accounts(identity.user.id, organization_id), offset, limit)


@router.post(
    "/organizations/{organization_id}/accounts",
    response_model=AccountResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_account(
    organization_id: str,
    payload: AccountCreate,
    identity: IdentityDep,
    engine: EngineDep,
    _role: AccountRole,
) -> dict[str, object]:
    account_id = engine.create_account(
        identity.user.id, organization_id, payload.code, payload.name, payload.account_type
    )
    return engine.get_account(identity.user.id, organization_id, account_id)


@router.get(
    "/organizations/{organization_id}/accounts/{account_id}", response_model=AccountResponse
)
def get_account(
    organization_id: str,
    account_id: str,
    identity: IdentityDep,
    engine: EngineDep,
    _role: ViewRole,
) -> dict[str, object]:
    return engine.get_account(identity.user.id, organization_id, account_id)


@router.patch(
    "/organizations/{organization_id}/accounts/{account_id}", response_model=AccountResponse
)
def update_account(
    organization_id: str,
    account_id: str,
    payload: AccountUpdate,
    identity: IdentityDep,
    engine: EngineDep,
    _role: AccountRole,
) -> dict[str, object]:
    engine.set_account_active(identity.user.id, organization_id, account_id, payload.active)
    return engine.get_account(identity.user.id, organization_id, account_id)


@router.get("/organizations/{organization_id}/periods", response_model=list[PeriodResponse])
def list_periods(
    organization_id: str, identity: IdentityDep, engine: EngineDep, _role: ViewRole
) -> tuple[dict[str, object], ...]:
    return engine.list_periods(identity.user.id, organization_id)


@router.post(
    "/organizations/{organization_id}/periods",
    response_model=PeriodResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_period(
    organization_id: str,
    payload: PeriodCreate,
    identity: IdentityDep,
    engine: EngineDep,
    _role: PeriodRole,
) -> dict[str, object]:
    period_id = engine.create_period(
        identity.user.id, organization_id, payload.name, payload.starts_on, payload.ends_on
    )
    return next(
        period
        for period in engine.list_periods(identity.user.id, organization_id)
        if period["id"] == period_id
    )


@router.post(
    "/organizations/{organization_id}/periods/{period_id}/lock",
    response_model=PeriodResponse,
)
def lock_period(
    organization_id: str,
    period_id: str,
    identity: IdentityDep,
    engine: EngineDep,
    _role: LockRole,
) -> dict[str, object]:
    engine.lock_period(identity.user.id, organization_id, period_id)
    return next(
        period
        for period in engine.list_periods(identity.user.id, organization_id)
        if period["id"] == period_id
    )


@router.post(
    "/organizations/{organization_id}/proposals",
    response_model=ProposalResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_proposal(
    organization_id: str,
    payload: ProposalCreate,
    identity: IdentityDep,
    engine: EngineDep,
    _role: ProposalRole,
) -> dict[str, object]:
    transaction_id = engine.create_transaction(
        identity.user.id,
        organization_id,
        payload.entry_date,
        payload.description,
        tuple(
            LineInput(line.account_id, line.debit, line.credit, line.project_id)
            for line in payload.lines
        ),
        document_id=payload.document_id,
    )
    return engine.get_transaction(identity.user.id, organization_id, transaction_id)


@router.get(
    "/organizations/{organization_id}/proposals/{proposal_id}",
    response_model=ProposalResponse,
)
def get_proposal(
    organization_id: str,
    proposal_id: str,
    identity: IdentityDep,
    engine: EngineDep,
    _role: ViewRole,
) -> dict[str, object]:
    return engine.get_transaction(identity.user.id, organization_id, proposal_id)


@router.post(
    "/organizations/{organization_id}/proposals/{proposal_id}/validate",
    response_model=ValidationResponse,
)
def validate_proposal(
    organization_id: str,
    proposal_id: str,
    identity: IdentityDep,
    engine: EngineDep,
    _role: ProposalRole,
) -> dict[str, object]:
    return asdict(engine.validate_transaction(identity.user.id, organization_id, proposal_id))


@router.post(
    "/organizations/{organization_id}/proposals/{proposal_id}/confirm",
    response_model=ConfirmationResponse,
)
def confirm_proposal(
    organization_id: str,
    proposal_id: str,
    payload: ConfirmationRequest,
    idempotency_key: IdempotencyKey,
    identity: IdentityDep,
    engine: EngineDep,
    _role: ConfirmRole,
) -> dict[str, object]:
    request_fingerprint = _fingerprint(
        {
            "organization_id": organization_id,
            "proposal_id": proposal_id,
            **payload.model_dump(mode="json"),
        }
    )
    confirmation = engine.confirm_transaction(
        identity.user.id,
        organization_id,
        payload.validation_id,
        accepted=payload.accepted,
        proposal_id=proposal_id,
        proposal_version=payload.proposal_version,
        confirmation_request_id=idempotency_key,
        idempotency_key=idempotency_key,
        request_fingerprint=request_fingerprint,
    )
    return engine.get_confirmation(identity.user.id, organization_id, confirmation.id)


@router.post(
    "/organizations/{organization_id}/proposals/{proposal_id}/post",
    response_model=PostResponse,
)
def post_proposal(
    organization_id: str,
    proposal_id: str,
    payload: PostRequest,
    idempotency_key: IdempotencyKey,
    identity: IdentityDep,
    engine: EngineDep,
    _role: PostRole,
) -> dict[str, str]:
    request_fingerprint = _fingerprint(
        {
            "organization_id": organization_id,
            "proposal_id": proposal_id,
            **payload.model_dump(mode="json"),
        }
    )
    confirmation = engine.get_confirmation(
        identity.user.id, organization_id, payload.confirmation_id
    )
    if confirmation["proposal_id"] != proposal_id:
        raise ChatbookError("not_found", "Confirmation does not belong to this proposal.")
    entry_id = engine.post_transaction(
        identity.user.id,
        organization_id,
        payload.confirmation_id,
        idempotency_key=idempotency_key,
        request_fingerprint=request_fingerprint,
    )
    return {"entry_id": entry_id}


@router.post(
    "/organizations/{organization_id}/journal-entries/{entry_id}/reversals",
    response_model=ProposalResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_reversal(
    organization_id: str,
    entry_id: str,
    payload: ReversalRequest,
    identity: IdentityDep,
    engine: EngineDep,
    _role: ReversalRole,
) -> dict[str, object]:
    proposal_id = engine.propose_reversal(
        identity.user.id, organization_id, entry_id, payload.entry_date, payload.reason
    )
    return engine.get_transaction(identity.user.id, organization_id, proposal_id)


@router.get(
    "/organizations/{organization_id}/journal-entries",
    response_model=Page[JournalEntrySummaryResponse],
)
def list_journal_entries(
    organization_id: str,
    identity: IdentityDep,
    engine: EngineDep,
    _role: ViewRole,
    offset: Offset = 0,
    limit: Limit = 50,
) -> dict[str, object]:
    return _page(engine.list_journal_entries(identity.user.id, organization_id), offset, limit)


@router.get(
    "/organizations/{organization_id}/journal-entries/{entry_id}",
    response_model=JournalEntryResponse,
)
def get_journal_entry(
    organization_id: str,
    entry_id: str,
    identity: IdentityDep,
    engine: EngineDep,
    _role: ViewRole,
) -> dict[str, object]:
    return engine.get_journal_entry(identity.user.id, organization_id, entry_id)


@router.get(
    "/organizations/{organization_id}/reports/general-ledger",
    response_model=Page[LedgerLineResponse],
)
def general_ledger(
    organization_id: str,
    identity: IdentityDep,
    engine: EngineDep,
    _role: ReportRole,
    as_of: str | None = None,
    starts_on: str | None = None,
    project_id: str | None = None,
    offset: Offset = 0,
    limit: Limit = 50,
) -> dict[str, object]:
    lines = engine.ledger(
        identity.user.id,
        organization_id,
        as_of=as_of,
        starts_on=starts_on,
        project_id=project_id,
    )
    return _page(lines, offset, limit)


@router.get(
    "/organizations/{organization_id}/reports/trial-balance",
    response_model=TrialBalanceResponse,
)
def trial_balance(
    organization_id: str,
    identity: IdentityDep,
    engine: EngineDep,
    _role: ReportRole,
    as_of: str | None = None,
    project_id: str | None = None,
) -> dict[str, object]:
    return _trial_response(
        engine.trial_balance(identity.user.id, organization_id, as_of=as_of, project_id=project_id)
    )


@router.get(
    "/organizations/{organization_id}/reports/income-statement",
    response_model=IncomeStatementResponse,
)
def income_statement(
    organization_id: str,
    starts_on: str,
    ends_on: str,
    identity: IdentityDep,
    engine: EngineDep,
    _role: ReportRole,
) -> dict[str, object]:
    return engine.income_statement(identity.user.id, organization_id, starts_on, ends_on)


@router.get(
    "/organizations/{organization_id}/reports/balance-sheet",
    response_model=BalanceSheetResponse,
)
def balance_sheet(
    organization_id: str,
    as_of: str,
    identity: IdentityDep,
    engine: EngineDep,
    _role: ReportRole,
) -> dict[str, object]:
    return engine.balance_sheet(identity.user.id, organization_id, as_of)


@router.get(
    "/organizations/{organization_id}/reports/cash-flow",
    response_model=CashFlowResponse,
)
def cash_flow(
    organization_id: str,
    starts_on: str,
    ends_on: str,
    cash_account_id: Annotated[list[str], Query()],
    identity: IdentityDep,
    engine: EngineDep,
    _role: ReportRole,
) -> dict[str, object]:
    return engine.cash_flow(identity.user.id, organization_id, starts_on, ends_on, cash_account_id)


@router.get(
    "/organizations/{organization_id}/audit-events", response_model=Page[AuditEventResponse]
)
def audit_events(
    organization_id: str,
    identity: IdentityDep,
    engine: EngineDep,
    _role: AuditRole,
    entity_id: str | None = None,
    offset: Offset = 0,
    limit: Limit = 50,
) -> dict[str, object]:
    events = engine.audit_events(identity.user.id, organization_id, entity_id=entity_id)
    return _page(events, offset, limit)


def create_app(
    database_path: str | Path | None = None,
    *,
    session_ttl_seconds: int = 28_800,
    canonical_rehearsal: bool = False,
    runtime_configuration: RuntimeConfiguration | None = None,
    maintenance_gate: MaintenanceGate | None = None,
) -> FastAPI:
    if canonical_rehearsal and runtime_configuration is not None:
        raise ChatbookError(
            "runtime_configuration_conflict",
            "Rehearsal and normal runtime configuration cannot be combined.",
        )
    if canonical_rehearsal:
        path = str(database_path or os.getenv("CHATBOOK_DB_PATH", "chatbook.db"))
        bootstrap = AccountingEngine.for_canonical_rehearsal(path)
        selected_runtime = None
    else:
        selected_runtime = runtime_configuration or (
            RuntimeConfiguration.from_environment()
            if database_path is None
            else RuntimeConfiguration.organization_v3(database_path)
        )
        path = selected_runtime.database_path
        bootstrap = AccountingEngine.for_runtime(selected_runtime)
    bootstrap.close()
    selected_maintenance = maintenance_gate or MaintenanceGate.from_environment()
    operational_log_path = os.getenv(OPERATIONAL_EVENT_LOG_ENV)
    operational_event_sink = (
        None if operational_log_path is None else OperationalEventSink(operational_log_path)
    )

    @asynccontextmanager
    async def lifespan(_application: FastAPI) -> AsyncIterator[None]:
        if selected_maintenance is not None:
            await selected_maintenance.start()
        try:
            yield
        finally:
            if selected_maintenance is not None:
                await selected_maintenance.stop()

    application = FastAPI(
        title="Chatbooks API",
        version="0.2.0",
        description="Authenticated application boundary for the deterministic accounting engine.",
        lifespan=lifespan,
    )
    application.state.database_path = path
    application.state.session_ttl_seconds = session_ttl_seconds
    application.state.canonical_rehearsal = canonical_rehearsal
    application.state.runtime_configuration = selected_runtime
    application.state.maintenance_gate = selected_maintenance
    application.state.operational_event_sink = operational_event_sink
    application.add_middleware(RequestLoggingMiddleware)
    if selected_maintenance is not None:
        application.add_middleware(MaintenanceMiddleware, gate=selected_maintenance)
    application.add_exception_handler(ChatbookError, _chatbook_error_handler)
    application.add_exception_handler(StarletteHTTPException, _http_error_handler)
    application.add_exception_handler(RequestValidationError, _validation_error_handler)
    application.add_exception_handler(Exception, _unexpected_error_handler)
    application.include_router(router)
    return application


def run() -> None:
    maintenance_paths = MaintenancePaths.from_environment()
    if maintenance_paths is None:
        uvicorn.run(
            "chatbook.api.main:create_app",
            factory=True,
            host=os.getenv("CHATBOOK_HOST", "127.0.0.1"),
            port=int(os.getenv("CHATBOOK_PORT", "8000")),
            workers=1,
        )
        return

    async def controlled_server() -> None:
        server = uvicorn.Server(
            uvicorn.Config(
                "chatbook.api.main:create_app",
                factory=True,
                host=os.getenv("CHATBOOK_HOST", "127.0.0.1"),
                port=int(os.getenv("CHATBOOK_PORT", "8000")),
                workers=1,
            )
        )

        async def watch_shutdown() -> None:
            while not server.should_exit:
                if shutdown_requested(maintenance_paths):
                    server.should_exit = True
                    return
                await asyncio.sleep(0.1)

        watcher = asyncio.create_task(watch_shutdown())
        try:
            await server.serve()
        finally:
            watcher.cancel()

    asyncio.run(controlled_server())
