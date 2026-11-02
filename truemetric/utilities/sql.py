import logging
import re

logger = logging.getLogger(__name__)

_IDENTIFIER = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


def quote_identifier(name: str) -> str:
    """
    #Feature: Warehouse guardrails
    #Scenario: Quote a column or table name after validating it as a plain identifier
    #Complexity: Time O(n)

    Args:
        name: Identifier.

    Returns:
        Double-quoted identifier.

    Raises:
        ValueError: When name is None or not a plain identifier.
    """
    try:
        if name is None:
            raise ValueError("[quote_identifier] 'name' is required.")
        if not _IDENTIFIER.fullmatch(name):
            raise ValueError(
                f"[quote_identifier] Invalid identifier {name!r}. Invariant violated: letters, digits and "
                "underscores only. Fix: correct the name in configuration."
            )
        return f'"{name}"'
    except Exception as exc:
        logger.error("quote_identifier failed: %s", exc)
        raise


def quote_literal(value: str) -> str:
    """
    #Feature: Warehouse guardrails
    #Scenario: Quote a string literal for a MetricFlow where filter
    #Complexity: Time O(n)

    Args:
        value: Raw string value.

    Returns:
        Single-quoted literal with embedded quotes doubled.

    Raises:
        ValueError: When value is None.
    """
    try:
        if value is None:
            raise ValueError("[quote_literal] 'value' is required.")
        return "'" + str(value).replace("'", "''") + "'"
    except Exception as exc:
        logger.error("quote_literal failed: %s", exc)
        raise
