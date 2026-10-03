"""Immutable domain values and exact arithmetic; independent of persistence and UI."""

import re
from dataclasses import dataclass
from datetime import date
from enum import StrEnum

MAX_AMOUNT = 9_000_000_000_000
MAX_LINES = 1_000


class ChatbookError(Exception):
    """An expected, user-actionable domain failure with a stable error code."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class AccountType(StrEnum):
    ASSET = "asset"
    LIABILITY = "liability"
    EQUITY = "equity"
    REVENUE = "revenue"
    EXPENSE = "expense"


class ProjectStatus(StrEnum):
    PLANNED = "planned"
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class OrganizationRole(StrEnum):
    OWNER = "OWNER"
    ADMIN = "ADMIN"
    ACCOUNTANT = "ACCOUNTANT"
    MEMBER = "MEMBER"
    VIEWER = "VIEWER"


@dataclass(frozen=True, slots=True)
class LineInput:
    account_id: str
    debit: int = 0
    credit: int = 0
    project_id: str | None = None


@dataclass(frozen=True, slots=True)
class Validation:
    id: str
    transaction_id: str
    fingerprint: str
    debit_total: int
    credit_total: int


@dataclass(frozen=True, slots=True)
class Confirmation:
    id: str
    transaction_id: str
    actor_id: str


@dataclass(frozen=True, slots=True)
class Balance:
    account_id: str
    code: str
    name: str
    account_type: AccountType
    debits: int
    credits: int

    @property
    def net_debit(self) -> int:
        return self.debits - self.credits

    @property
    def debit_balance(self) -> int:
        return max(self.net_debit, 0)

    @property
    def credit_balance(self) -> int:
        return max(-self.net_debit, 0)


@dataclass(frozen=True, slots=True)
class TrialBalance:
    currency: str
    minor_unit_digits: int
    as_of: str | None
    project_id: str | None
    accounts: tuple[Balance, ...]

    @property
    def total_debits(self) -> int:
        return sum(account.debit_balance for account in self.accounts)

    @property
    def total_credits(self) -> int:
        return sum(account.credit_balance for account in self.accounts)

    @property
    def balanced(self) -> bool:
        return self.total_debits == self.total_credits


def canonical_date(value: str, field: str = "date") -> str:
    try:
        parsed = date.fromisoformat(value)
    except (ValueError, TypeError) as exc:
        raise ChatbookError("invalid_date", f"{field} must be a valid YYYY-MM-DD date.") from exc
    if parsed.isoformat() != value:
        raise ChatbookError("invalid_date", f"{field} must use YYYY-MM-DD.")
    return value


def amount(value: int, field: str = "amount") -> int:
    if type(value) is not int or not 0 <= value <= MAX_AMOUNT:
        raise ChatbookError(
            "invalid_amount", f"{field} must be an integer from 0 to {MAX_AMOUNT} minor units."
        )
    return value


def parse_amount(value: str, minor_unit_digits: int) -> int:
    """Parse text without rounding, binary floats, scientific notation, or locale guessing."""
    if type(minor_unit_digits) is not int or not 0 <= minor_unit_digits <= 6:
        raise ChatbookError("invalid_precision", "Minor unit digits must be between 0 and 6.")
    if not isinstance(value, str) or not re.fullmatch(r"[0-9]+(?:\.[0-9]+)?", value):
        raise ChatbookError("invalid_amount", "Use a nonnegative decimal amount, such as 12.50.")
    whole, _, fraction = value.partition(".")
    if len(fraction) > minor_unit_digits or len(whole) > 13:
        raise ChatbookError("invalid_amount", "Amount exceeds the supported precision or size.")
    units = int(whole) * 10**minor_unit_digits
    units += int(fraction.ljust(minor_unit_digits, "0") or "0")
    return amount(units)


def validate_lines(lines: tuple[LineInput, ...]) -> tuple[int, int]:
    if not 2 <= len(lines) <= MAX_LINES:
        raise ChatbookError("invalid_line_count", f"A journal requires 2 to {MAX_LINES} lines.")
    for line in lines:
        amount(line.debit, "debit")
        amount(line.credit, "credit")
        if (line.debit > 0) == (line.credit > 0):
            raise ChatbookError("invalid_line", "Each line must have exactly one positive side.")
    debits = sum(line.debit for line in lines)
    credits = sum(line.credit for line in lines)
    if debits != credits:
        raise ChatbookError(
            "unbalanced_entry", f"Debits ({debits}) differ from credits ({credits})."
        )
    return debits, credits
