import logging
from datetime import date, datetime, time
from decimal import Decimal
from typing import Any

logger = logging.getLogger(__name__)


def to_plain(value: Any) -> Any:
    """
    #Feature: Semantic layer
    #Scenario: Convert warehouse values to JSON-friendly Python values
    #Complexity: Time O(1)

    Args:
        value: Raw cell value.

    Returns:
        float for Decimal, ISO date string for midnight datetimes and dates, else the value.
    """
    try:
        if isinstance(value, Decimal):
            return float(value)
        if isinstance(value, datetime):
            return value.date().isoformat() if value.time() == time(0) else value.isoformat()
        if isinstance(value, date):
            return value.isoformat()
        return value
    except Exception as exc:
        logger.error("to_plain failed: %s", exc)
        raise
