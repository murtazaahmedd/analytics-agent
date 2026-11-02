import logging
from datetime import datetime, timezone
from pathlib import Path

from truemetric.constants import (
    BEARER_PREFIX,
    SQLSTATE_BAD_REQUEST,
    SQLSTATE_FOREIGN_KEY_VIOLATION,
    SQLSTATE_FORBIDDEN,
    SQLSTATE_NOT_FOUND,
    SQLSTATE_RATE_LIMITED,
    SQLSTATE_UNIQUE_VIOLATION,
)
from truemetric.errors import Errors

logger = logging.getLogger(__name__)

_SQLSTATE_ERRORS: dict[str, type[Exception]] = {
    SQLSTATE_BAD_REQUEST: Errors.HTTP.BadRequest,
    SQLSTATE_FORBIDDEN: Errors.HTTP.Forbidden,
    SQLSTATE_NOT_FOUND: Errors.HTTP.NotFound,
    SQLSTATE_RATE_LIMITED: Errors.Misc.RateLimitExceeded,
    SQLSTATE_UNIQUE_VIOLATION: Errors.Database.IntegrityError,
    SQLSTATE_FOREIGN_KEY_VIOLATION: Errors.Database.IntegrityError,
}


def bearer_token(header: str | None) -> str | None:
    """
    #Feature: Authentication
    #Scenario: Pull the token out of an "Authorization: Bearer <token>" header
    #Complexity: Time O(len(header))

    Args:
        header: Raw Authorization header, or None.

    Returns:
        The token, or None when the header is missing or not a bearer token.
    """
    try:
        if not header or not header.lower().startswith(BEARER_PREFIX):
            return None
        return header[len(BEARER_PREFIX):].strip() or None
    except Exception as exc:
        logger.error("bearer_token failed: %s", exc)
        raise


def naive_utc(value: datetime | None) -> datetime | None:
    """
    #Feature: Workspaces
    #Scenario: Warehouse clocks are naive; a client may send a pinned clock with a timezone
    #Complexity: Time O(1)

    Args:
        value: Datetime, aware or naive, or None.

    Returns:
        The same instant as naive UTC; naive values are returned unchanged.
    """
    try:
        if value is None or value.tzinfo is None:
            return value
        return value.astimezone(timezone.utc).replace(tzinfo=None)
    except Exception as exc:
        logger.error("naive_utc failed: %s", exc)
        raise


def resolve_inside(path: str, root: Path) -> Path:
    """
    #Feature: Workspaces
    #Scenario: A workspace path must exist and resolve inside the allowed root (no ../ escapes, no symlink escapes)
    #Complexity: Time O(path depth)

    Args:
        path: Path as given by the client, absolute or relative to root.
        root: Allowed root directory.

    Returns:
        The resolved absolute path.

    Raises:
        ValueError: When path or root is None.
        Errors.HTTP.BadRequest: When the path does not exist or is outside root.
    """
    try:
        if path is None or root is None:
            raise ValueError("[resolve_inside] 'path' and 'root' are required.")
        base = root.resolve()
        resolved = (base / path).resolve()
        if not resolved.is_relative_to(base) or not resolved.exists():
            raise Errors.HTTP.BadRequest(
                f"[resolve_inside] Path {path!r} is not usable. Invariant violated: workspace paths must exist "
                "inside the workspace root. Fix: pass a path under the configured TRUEMETRIC_WORKSPACE_ROOT."
            )
        return resolved
    except Exception as exc:
        logger.warning("resolve_inside rejected path: %s", exc)
        raise


def sqlstate_of(exc: BaseException) -> str | None:
    """
    #Feature: Control-plane database
    #Scenario: Find the SQLSTATE on a driver error, however deeply SQLAlchemy wrapped it
    #Complexity: Time O(cause chain length)

    Args:
        exc: Any exception.

    Returns:
        The SQLSTATE code, or None.
    """
    try:
        current: BaseException | None = exc
        while current is not None:
            code = getattr(current, "sqlstate", None)
            if code:
                return code
            current = getattr(current, "orig", None) or current.__cause__
        return None
    except Exception as err:
        logger.error("sqlstate_of failed: %s", err)
        raise


def translate_db_error(exc: Exception, operation: str) -> Exception:
    """
    #Feature: Control-plane database
    #Scenario: Map a UDF error to the domain error taxonomy so the HTTP layer can pick a status code
    #Complexity: Time O(cause chain length)

    Args:
        exc: Error raised while calling an api.* UDF.
        operation: "Class.method" for the message.

    Returns:
        A domain error, or the original error when its SQLSTATE is not mapped.
    """
    try:
        error_type = _SQLSTATE_ERRORS.get(sqlstate_of(exc) or "")
        if error_type is None:
            return exc
        detail = str(getattr(exc, "orig", exc)).split("\n")[0]
        return error_type(f"[{operation}] {detail}")
    except Exception as err:
        logger.error("translate_db_error failed: %s", err)
        raise
