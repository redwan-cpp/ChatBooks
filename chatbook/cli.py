"""A small, explicit manual interface; JSON output uses integer minor units."""

import argparse
import json
import sqlite3
import sys
from collections.abc import Sequence
from dataclasses import asdict
from pathlib import Path

from .domain import AccountType, ChatbookError, LineInput, ProjectStatus, TrialBalance
from .engine import AccountingEngine
from .runtime import RuntimeConfiguration


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="chatbook", description="Chatbooks accounting foundation")
    parser.add_argument("--db", help="Local SQLite database path; schema mode is deployment-only")
    parser.add_argument("--actor", help="Trusted local user ID")
    parser.add_argument("--org", help="Organization ID")
    commands = parser.add_subparsers(dest="command", required=True)

    user = commands.add_parser("user-create", help="Register a local user")
    user.add_argument("--name", required=True)
    org = commands.add_parser("org-create", help="Create an organization and empty chart")
    org.add_argument("--name", required=True)
    org.add_argument("--currency", required=True)
    org.add_argument("--minor-unit-digits", type=int, required=True)
    member = commands.add_parser("member-add")
    member.add_argument("--user", required=True)
    account = commands.add_parser("account-create")
    account.add_argument("--code", required=True)
    account.add_argument("--name", required=True)
    account.add_argument("--type", choices=list(AccountType), required=True)
    active = commands.add_parser("account-status")
    active.add_argument("--account", required=True)
    active.add_argument("--active", choices=["true", "false"], required=True)
    period = commands.add_parser("period-create")
    period.add_argument("--name", required=True)
    period.add_argument("--start", required=True)
    period.add_argument("--end", required=True)
    lock = commands.add_parser("period-lock")
    lock.add_argument("--period", required=True)
    project = commands.add_parser("project-create")
    project.add_argument("--name", required=True)
    project.add_argument("--description", default="")
    project.add_argument("--client")
    project.add_argument("--expected-revenue", type=int, help="Integer minor units")
    project.add_argument("--budget", type=int, help="Integer minor units")
    project.add_argument("--start")
    project.add_argument("--end")
    project.add_argument("--status", choices=list(ProjectStatus), default="planned")
    document = commands.add_parser("document-register", help="Register metadata; no extraction")
    for field in ("filename", "media-type", "sha256", "storage-reference"):
        document.add_argument(f"--{field}", required=True)
    create = commands.add_parser("create", help="Create a manual proposal from a JSON file")
    create.add_argument("--file", type=Path, required=True)
    show = commands.add_parser("show", help="Inspect the proposal before confirmation")
    show.add_argument("--transaction", required=True)
    validate = commands.add_parser("validate")
    validate.add_argument("--transaction", required=True)
    confirm = commands.add_parser("confirm", help="Review and explicitly confirm a validation")
    confirm.add_argument("--validation", required=True)
    confirm.add_argument(
        "--accept", action="store_true", help="Explicitly accept the displayed proposal"
    )
    post = commands.add_parser("post")
    post.add_argument("--confirmation", required=True)
    reverse = commands.add_parser(
        "reverse", help="Propose a reversal; validate and confirm it separately"
    )
    reverse.add_argument("--entry", required=True)
    reverse.add_argument("--date", required=True)
    reverse.add_argument("--reason", required=True)
    for name in ("ledger", "trial-balance"):
        report = commands.add_parser(name)
        report.add_argument("--as-of")
        report.add_argument("--project")
    balance = commands.add_parser("balance")
    balance.add_argument("--account", required=True)
    balance.add_argument("--as-of")
    income = commands.add_parser("income-statement")
    income.add_argument("--start", required=True)
    income.add_argument("--end", required=True)
    sheet = commands.add_parser("balance-sheet")
    sheet.add_argument("--as-of", required=True)
    audit = commands.add_parser("audit")
    audit.add_argument("--entity")
    commands.add_parser("catalog", help="List accounts, periods, projects, and document metadata")
    return parser


def _load_proposal(path: Path) -> tuple[str, str, tuple[LineInput, ...], str | None]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ChatbookError("invalid_input", "Proposal must be a JSON object.")
    allowed = {"entry_date", "description", "lines", "document_id"}
    if set(payload) - allowed or not {"entry_date", "description", "lines"} <= set(payload):
        raise ChatbookError(
            "invalid_input", "Use entry_date, description, lines, and optional document_id."
        )
    if not isinstance(payload["entry_date"], str) or not isinstance(payload["description"], str):
        raise ChatbookError("invalid_input", "entry_date and description must be strings.")
    if not isinstance(payload["lines"], list):
        raise ChatbookError("invalid_input", "lines must be an array.")
    lines: list[LineInput] = []
    for row in payload["lines"]:
        if not isinstance(row, dict) or "account_id" not in row:
            raise ChatbookError("invalid_input", "Each line must have an account_id.")
        if set(row) - {"account_id", "debit", "credit", "project_id"}:
            raise ChatbookError("invalid_input", "Unknown proposal line field.")
        if not isinstance(row["account_id"], str) or (
            row.get("project_id") is not None and not isinstance(row["project_id"], str)
        ):
            raise ChatbookError("invalid_input", "Account and project IDs must be strings.")
        lines.append(
            LineInput(
                row["account_id"], row.get("debit", 0), row.get("credit", 0), row.get("project_id")
            )
        )
    document = payload.get("document_id")
    if document is not None and not isinstance(document, str):
        raise ChatbookError("invalid_input", "document_id must be a string.")
    return payload["entry_date"], payload["description"], tuple(lines), document


def _trial_json(report: TrialBalance) -> dict[str, object]:
    result: dict[str, object] = asdict(report)
    result["accounts"] = [
        {
            **asdict(account),
            "net_debit": account.net_debit,
            "debit_balance": account.debit_balance,
            "credit_balance": account.credit_balance,
        }
        for account in report.accounts
    ]
    result.update(
        total_debits=report.total_debits,
        total_credits=report.total_credits,
        balanced=report.balanced,
    )
    if report.project_id:
        result["note"] = "Project-filtered lines are a dimensional view and may not balance."
    return result


def _run(engine: AccountingEngine, args: argparse.Namespace) -> object:
    command = args.command
    if command == "user-create":
        return {"user_id": engine.create_user(args.name)}
    if not args.actor:
        raise ChatbookError("actor_required", "Provide --actor before the command.")
    actor = str(args.actor)
    if command == "org-create":
        return {
            "organization_id": engine.create_organization(
                actor, args.name, args.currency, args.minor_unit_digits
            )
        }
    if not args.org:
        raise ChatbookError("organization_required", "Provide --org before the command.")
    org = str(args.org)
    match command:
        case "member-add":
            engine.add_member(actor, org, args.user)
            return {"added": args.user}
        case "account-create":
            return {
                "account_id": engine.create_account(
                    actor, org, args.code, args.name, AccountType(args.type)
                )
            }
        case "account-status":
            engine.set_account_active(actor, org, args.account, args.active == "true")
            return {"account_id": args.account, "active": args.active == "true"}
        case "period-create":
            return {"period_id": engine.create_period(actor, org, args.name, args.start, args.end)}
        case "period-lock":
            engine.lock_period(actor, org, args.period)
            return {"period_id": args.period, "locked": True}
        case "project-create":
            return {
                "project_id": engine.create_project(
                    actor,
                    org,
                    args.name,
                    description=args.description,
                    client=args.client,
                    expected_revenue=args.expected_revenue,
                    budget=args.budget,
                    starts_on=args.start,
                    ends_on=args.end,
                    status=ProjectStatus(args.status),
                )
            }
        case "document-register":
            return {
                "document_id": engine.register_document(
                    actor, org, args.filename, args.media_type, args.sha256, args.storage_reference
                )
            }
        case "create":
            entry_date, description, lines, document = _load_proposal(args.file)
            return {
                "transaction_id": engine.create_transaction(
                    actor, org, entry_date, description, lines, document_id=document
                )
            }
        case "show":
            return engine.get_transaction(actor, org, args.transaction)
        case "validate":
            return asdict(engine.validate_transaction(actor, org, args.transaction))
        case "confirm":
            proposal = engine.proposal_for_validation(actor, org, args.validation)
            print(json.dumps(proposal, indent=2), file=sys.stderr)
            accepted = args.accept
            if not accepted:
                phrase = f"CONFIRM {proposal['id']}"
                print(
                    f"Amounts above are integer minor units. Type '{phrase}' to accept:",
                    file=sys.stderr,
                )
                accepted = sys.stdin.readline().strip() == phrase
            return asdict(
                engine.confirm_transaction(actor, org, args.validation, accepted=accepted)
            )
        case "post":
            return {"entry_id": engine.post_transaction(actor, org, args.confirmation)}
        case "reverse":
            return {
                "transaction_id": engine.propose_reversal(
                    actor, org, args.entry, args.date, args.reason
                )
            }
        case "ledger":
            return engine.ledger(actor, org, as_of=args.as_of, project_id=args.project)
        case "trial-balance":
            return _trial_json(
                engine.trial_balance(actor, org, as_of=args.as_of, project_id=args.project)
            )
        case "balance":
            balance = engine.account_balance(actor, org, args.account, as_of=args.as_of)
            return {
                **asdict(balance),
                "net_debit": balance.net_debit,
                "debit_balance": balance.debit_balance,
                "credit_balance": balance.credit_balance,
            }
        case "income-statement":
            return engine.income_statement(actor, org, args.start, args.end)
        case "balance-sheet":
            return engine.balance_sheet(actor, org, args.as_of)
        case "audit":
            return engine.audit_events(actor, org, entity_id=args.entity)
        case "catalog":
            return engine.catalog(actor, org)
    raise ChatbookError("unknown_command", "Unknown command.")


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    engine: AccountingEngine | None = None
    try:
        configuration = RuntimeConfiguration.from_environment(database_override=args.db)
        engine = AccountingEngine.for_runtime(configuration)
        result = _run(engine, args)
        print(json.dumps(result, indent=2))
        return 0
    except ChatbookError as exc:
        print(json.dumps({"error": exc.code, "message": str(exc)}), file=sys.stderr)
        return 2
    except (OSError, ValueError, sqlite3.Error) as exc:
        print(json.dumps({"error": "input_or_storage_error", "message": str(exc)}), file=sys.stderr)
        return 2
    finally:
        if engine:
            engine.close()
