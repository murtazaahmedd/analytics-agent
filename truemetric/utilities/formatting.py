import logging
from datetime import date
from typing import Any

from truemetric.constants import UNIT_FORMATS

logger = logging.getLogger(__name__)


def format_value(value: Any, unit: str) -> str:
    """
    #Feature: Answer formatting
    #Scenario: Render a metric value in its unit
    #Complexity: Time O(1)

    Args:
        value: Number or None.
        unit: currency, percent, count, hours or number.

    Returns:
        Display string; "no data" for None.
    """
    try:
        if value is None:
            return "no data"
        return UNIT_FORMATS.get(unit, UNIT_FORMATS["number"]).format(float(value))
    except Exception as exc:
        logger.error("format_value failed for unit=%s: %s", unit, exc)
        raise


def period_label(start: date | None, end: date | None) -> str:
    """
    #Feature: Answer formatting
    #Scenario: Always state the exact dates an answer covers
    #Complexity: Time O(1)

    Args:
        start: Inclusive start or None.
        end: Inclusive end or None.

    Returns:
        Human label.
    """
    try:
        if start and end:
            return f"{start.isoformat()} to {end.isoformat()}" if start != end else f"on {start.isoformat()}"
        if start:
            return f"since {start.isoformat()}"
        if end:
            return f"up to {end.isoformat()}"
        return "all time"
    except Exception as exc:
        logger.error("period_label failed: %s", exc)
        raise


def render_table(columns: list[str], rows: list[dict[str, Any]], metric: str, unit: str) -> str:
    """
    #Feature: Answer formatting
    #Scenario: Small markdown table for grouped answers
    #Complexity: Time O(rows * columns)

    Args:
        columns: Result columns.
        rows: Result rows.
        metric: Metric column name.
        unit: Metric unit.

    Returns:
        Markdown table.
    """
    try:
        headers = [c.split("__")[-1].replace("_", " ") for c in columns]
        lines = ["| " + " | ".join(headers) + " |", "|" + "---|" * len(columns)]
        for row in rows:
            cells = [format_value(row[c], unit) if c == metric else str(row[c]) for c in columns]
            lines.append("| " + " | ".join(cells) + " |")
        return "\n".join(lines)
    except Exception as exc:
        logger.error("render_table failed: %s", exc)
        raise
