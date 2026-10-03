"""Password and opaque-session authentication for the application boundary."""

import base64
import hashlib
import hmac
import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from secrets import token_bytes, token_urlsafe
from uuid import uuid4

from .canonical_database import CanonicalDatabase
from .database import Database
from .domain import ChatbookError
from .runtime import RuntimeConfiguration, open_runtime_database

_SCRYPT_N = 2**14
_SCRYPT_R = 8
_SCRYPT_P = 1
_DKLEN = 32
_DUMMY_SALT = b"chatbook-auth-v2"


@dataclass(frozen=True, slots=True)
class AuthenticatedUser:
    id: str
    name: str
    username: str


@dataclass(frozen=True, slots=True)
class SessionToken:
    access_token: str
    token_type: str
    expires_at: str
    user: AuthenticatedUser


def _now() -> datetime:
    return datetime.now(UTC)


def _normalize_username(value: str) -> str:
    if not isinstance(value, str):
        raise ChatbookError("invalid_username", "Username must be text.")
    normalized = value.strip().casefold()
    if not 3 <= len(normalized) <= 254 or not re.fullmatch(r"[^\s]+", normalized):
        raise ChatbookError(
            "invalid_username", "Username must be 3 to 254 characters without whitespace."
        )
    return normalized


def _validate_password(password: str) -> None:
    if not isinstance(password, str) or not 12 <= len(password) <= 1024:
        raise ChatbookError("invalid_password", "Password must be between 12 and 1024 characters.")


def _derive(password: str, salt: bytes) -> bytes:
    return hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=_SCRYPT_N,
        r=_SCRYPT_R,
        p=_SCRYPT_P,
        dklen=_DKLEN,
    )


def hash_password(password: str) -> str:
    _validate_password(password)
    salt = token_bytes(16)
    digest = _derive(password, salt)
    encoded_salt = base64.urlsafe_b64encode(salt).decode("ascii")
    encoded_digest = base64.urlsafe_b64encode(digest).decode("ascii")
    return f"scrypt${_SCRYPT_N}${_SCRYPT_R}${_SCRYPT_P}${encoded_salt}${encoded_digest}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, n, r, p, encoded_salt, encoded_digest = encoded.split("$", 5)
        if algorithm != "scrypt":
            return False
        salt = base64.urlsafe_b64decode(encoded_salt.encode("ascii"))
        expected = base64.urlsafe_b64decode(encoded_digest.encode("ascii"))
        actual = hashlib.scrypt(
            password.encode("utf-8"),
            salt=salt,
            n=int(n),
            r=int(r),
            p=int(p),
            dklen=len(expected),
        )
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


class AuthService:
    """Owns identity credentials and sessions; never returns a database connection."""

    def __init__(
        self,
        path: str | Path,
        *,
        session_ttl_seconds: int = 28_800,
        canonical_rehearsal: bool = False,
        runtime_configuration: RuntimeConfiguration | None = None,
        allow_thread_handoff: bool = False,
    ) -> None:
        if session_ttl_seconds <= 0:
            raise ValueError("Session lifetime must be positive.")
        if canonical_rehearsal and runtime_configuration is not None:
            raise ChatbookError(
                "runtime_configuration_conflict",
                "Rehearsal and normal runtime configuration cannot be combined.",
            )
        self._database: Database | CanonicalDatabase
        if runtime_configuration is not None:
            self._database = open_runtime_database(
                runtime_configuration, allow_thread_handoff=allow_thread_handoff
            )
        else:
            self._database = (
                CanonicalDatabase(path, allow_thread_handoff=allow_thread_handoff)
                if canonical_rehearsal
                else Database(path, allow_thread_handoff=allow_thread_handoff)
            )
        self._session_ttl = timedelta(seconds=session_ttl_seconds)

    def close(self) -> None:
        self._database.close()

    def register(self, name: str, username: str, password: str) -> AuthenticatedUser:
        display_name = name.strip() if isinstance(name, str) else ""
        if not display_name:
            raise ChatbookError("required_field", "name must not be empty.")
        normalized_username = _normalize_username(username)
        password_hash = hash_password(password)
        user_id = str(uuid4())
        try:
            with self._database.write(user_id, "user.register") as db:
                db.execute("INSERT INTO users (id, name) VALUES (?, ?)", (user_id, display_name))
                db.execute(
                    "INSERT INTO user_credentials (user_id, username, password_hash, created_at) "
                    "VALUES (?, ?, ?, ?)",
                    (user_id, normalized_username, password_hash, _now().isoformat()),
                )
        except ChatbookError as exc:
            if exc.code == "constraint_violation" and "username" in str(exc).lower():
                raise ChatbookError(
                    "username_taken", "That username is already registered."
                ) from exc
            raise
        return AuthenticatedUser(user_id, display_name, normalized_username)

    def login(self, username: str, password: str) -> SessionToken:
        normalized_username = _normalize_username(username)
        row = self._database.connection.execute(
            "SELECT u.id, u.name, c.username, c.password_hash FROM user_credentials c "
            "JOIN users u ON u.id = c.user_id WHERE c.username = ? COLLATE NOCASE",
            (normalized_username,),
        ).fetchone()
        if row is None:
            _derive(password, _DUMMY_SALT)
            raise ChatbookError("invalid_credentials", "Username or password is incorrect.")
        if not verify_password(password, str(row["password_hash"])):
            raise ChatbookError("invalid_credentials", "Username or password is incorrect.")
        raw_token = token_urlsafe(32)
        token_hash = hashlib.sha256(raw_token.encode("ascii")).hexdigest()
        created_at = _now()
        expires_at = created_at + self._session_ttl
        with self._database.write(str(row["id"]), "auth.login") as db:
            db.execute(
                "INSERT INTO auth_sessions ("
                "id, user_id, token_hash, created_at, expires_at, revoked_at) "
                "VALUES (?, ?, ?, ?, ?, NULL)",
                (
                    str(uuid4()),
                    row["id"],
                    token_hash,
                    created_at.isoformat(),
                    expires_at.isoformat(),
                ),
            )
        user = AuthenticatedUser(str(row["id"]), str(row["name"]), str(row["username"]))
        return SessionToken(raw_token, "bearer", expires_at.isoformat(), user)

    def authenticate(self, raw_token: str) -> AuthenticatedUser:
        token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
        row = self._database.connection.execute(
            "SELECT u.id, u.name, c.username, s.expires_at FROM auth_sessions s "
            "JOIN users u ON u.id = s.user_id "
            "JOIN user_credentials c ON c.user_id = u.id "
            "WHERE s.token_hash = ? AND s.revoked_at IS NULL",
            (token_hash,),
        ).fetchone()
        if row is None or datetime.fromisoformat(str(row["expires_at"])) <= _now():
            raise ChatbookError("authentication_required", "A valid bearer token is required.")
        return AuthenticatedUser(str(row["id"]), str(row["name"]), str(row["username"]))

    def logout(self, raw_token: str) -> None:
        token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
        row = self._database.connection.execute(
            "SELECT id, user_id, revoked_at FROM auth_sessions WHERE token_hash = ?", (token_hash,)
        ).fetchone()
        if row is None or row["revoked_at"] is not None:
            return
        with self._database.write(str(row["user_id"]), "auth.logout") as db:
            db.execute(
                "UPDATE auth_sessions SET revoked_at = ? WHERE id = ?",
                (_now().isoformat(), row["id"]),
            )

    def user_exists(self, user_id: str) -> bool:
        return (
            self._database.connection.execute(
                "SELECT 1 FROM users WHERE id = ?", (user_id,)
            ).fetchone()
            is not None
        )
