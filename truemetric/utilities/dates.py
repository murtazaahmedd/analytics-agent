import calendar
import logging
import re
from collections.abc import Callable
from datetime import date, timedelta

logger = logging.getLogger(__name__)

Period = tuple[date, date]

MONTHS = {name.lower(): i for i, name in enumerate(calendar.month_name) if name}
MONTHS.update({name.lower(): i for i, name in enumerate(calendar.month_abbr) if name})
_MONTH = "(" + "|".join(sorted(MONTHS, key=len, reverse=True)) + r")\.?"


def month_bounds(year: int, month: int) -> Period:
    """
    #Feature: Date parsing
    #Scenario: First and last day of a calendar month
    #Complexity: Time O(1)

    Args:
        year: Year.
        month: Month 1-12.

    Returns:
        (first day, last day).
    """
    try:
        return date(year, month, 1), date(year, month, calendar.monthrange(year, month)[1])
    except Exception as exc:
        logger.error("month_bounds failed for %s-%s: %s", year, month, exc)
        raise


def quarter_bounds(year: int, quarter: int) -> Period:
    """
    #Feature: Date parsing
    #Scenario: First and last day of a calendar quarter
    #Complexity: Time O(1)

    Args:
        year: Year.
        quarter: Quarter 1-4.

    Returns:
        (first day, last day).
    """
    try:
        return month_bounds(year, 3 * quarter - 2)[0], month_bounds(year, 3 * quarter)[1]
    except Exception as exc:
        logger.error("quarter_bounds failed for %s Q%s: %s", year, quarter, exc)
        raise


def shift_month(year: int, month: int, delta: int) -> tuple[int, int]:
    """
    #Feature: Date parsing
    #Scenario: Move a (year, month) pair by delta months
    #Complexity: Time O(1)

    Args:
        year: Year.
        month: Month 1-12.
        delta: Months to add (may be negative).

    Returns:
        (year, month).
    """
    try:
        index = year * 12 + month - 1 + delta
        return index // 12, index % 12 + 1
    except Exception as exc:
        logger.error("shift_month failed: %s", exc)
        raise


def same_bucket(start: date, end: date, grain: str) -> bool:
    """
    #Feature: Date parsing
    #Scenario: Whether a period fits inside one time bucket (so a series would have a single row)
    #Complexity: Time O(1)

    Args:
        start: Inclusive start.
        end: Inclusive end.
        grain: day, week, month, quarter or year.

    Returns:
        True when start and end fall in the same bucket.
    """
    try:
        keys = {
            "day": lambda d: d,
            "week": lambda d: d - timedelta(days=d.weekday()),
            "month": lambda d: (d.year, d.month),
            "quarter": lambda d: (d.year, (d.month - 1) // 3),
            "year": lambda d: d.year,
        }
        return keys[grain](start) == keys[grain](end)
    except Exception as exc:
        logger.error("same_bucket failed for grain=%s: %s", grain, exc)
        raise


def _explicit_range(text: str, today: date) -> Period | None:
    """
    #Feature: Date parsing
    #Scenario: "between 2024-01-01 and 2024-03-31" or "from X to Y"
    #Complexity: Time O(n)
    """
    try:
        match = re.search(r"(\d{4}-\d{2}-\d{2})\s+(?:and|to|-|through|until)\s+(\d{4}-\d{2}-\d{2})", text)
        return (date.fromisoformat(match.group(1)), date.fromisoformat(match.group(2))) if match else None
    except Exception as exc:
        logger.error("_explicit_range failed: %s", exc)
        raise


def _last_n(text: str, today: date) -> Period | None:
    """
    #Feature: Date parsing
    #Scenario: "last 7 days", "past 4 weeks", "last 3 months" (complete days ending yesterday)
    #Complexity: Time O(n)
    """
    try:
        match = re.search(r"(?:last|past|previous)\s+(\d+)\s+(day|week|month)s?", text)
        if not match:
            return None
        count, unit = int(match.group(1)), match.group(2)
        end = today - timedelta(days=1)
        if unit == "month":
            year, month = shift_month(today.year, today.month, -count)
            return date(year, month, 1), month_bounds(*shift_month(today.year, today.month, -1))[1]
        return end - timedelta(days=count * (7 if unit == "week" else 1) - 1), end
    except Exception as exc:
        logger.error("_last_n failed: %s", exc)
        raise


def _relative(text: str, today: date) -> Period | None:
    """
    #Feature: Date parsing
    #Scenario: yesterday, last/this week, month, quarter, year
    #Complexity: Time O(1)
    """
    try:
        monday = today - timedelta(days=today.weekday())
        quarter = (today.month - 1) // 3 + 1
        last_q = (today.year, quarter - 1) if quarter > 1 else (today.year - 1, 4)
        table = {
            "yesterday": (today - timedelta(days=1), today - timedelta(days=1)),
            "last week": (monday - timedelta(days=7), monday - timedelta(days=1)),
            "previous week": (monday - timedelta(days=7), monday - timedelta(days=1)),
            "this week": (monday, today),
            "last month": month_bounds(*shift_month(today.year, today.month, -1)),
            "previous month": month_bounds(*shift_month(today.year, today.month, -1)),
            "this month": (date(today.year, today.month, 1), today),
            "last quarter": quarter_bounds(*last_q),
            "this quarter": (quarter_bounds(today.year, quarter)[0], today),
            "last year": (date(today.year - 1, 1, 1), date(today.year - 1, 12, 31)),
            "this year": (date(today.year, 1, 1), today),
            "year to date": (date(today.year, 1, 1), today),
            "ytd": (date(today.year, 1, 1), today),
        }
        return next((period for phrase, period in table.items() if re.search(rf"\b{phrase}\b", text)), None)
    except Exception as exc:
        logger.error("_relative failed: %s", exc)
        raise


def _quarter(text: str, today: date) -> Period | None:
    """
    #Feature: Date parsing
    #Scenario: "Q3 2025" or "2025 Q3"
    #Complexity: Time O(n)
    """
    try:
        match = re.search(r"\bq([1-4])\s*(\d{4})\b", text) or re.search(r"\b(\d{4})\s*q([1-4])\b", text)
        if not match:
            return None
        first, second = int(match.group(1)), int(match.group(2))
        return quarter_bounds(second, first) if first <= 4 else quarter_bounds(first, second)
    except Exception as exc:
        logger.error("_quarter failed: %s", exc)
        raise


def _week_of(text: str, today: date) -> Period | None:
    """
    #Feature: Date parsing
    #Scenario: "week of 2026-10-19" (Monday to Sunday containing the date)
    #Complexity: Time O(n)
    """
    try:
        match = re.search(r"week of (\d{4}-\d{2}-\d{2})", text)
        if not match:
            return None
        day = date.fromisoformat(match.group(1))
        monday = day - timedelta(days=day.weekday())
        return monday, monday + timedelta(days=6)
    except Exception as exc:
        logger.error("_week_of failed: %s", exc)
        raise


def _single_day(text: str, today: date) -> Period | None:
    """
    #Feature: Date parsing
    #Scenario: "on 2026-10-30"
    #Complexity: Time O(n)
    """
    try:
        match = re.search(r"\b(\d{4}-\d{2}-\d{2})\b", text)
        return (date.fromisoformat(match.group(1)),) * 2 if match else None
    except Exception as exc:
        logger.error("_single_day failed: %s", exc)
        raise


def _month_range(text: str, today: date) -> Period | None:
    """
    #Feature: Date parsing
    #Scenario: "January to March 2026", "between July and September 2026", "Jan 2025 through Mar 2026"
    #Complexity: Time O(n)
    """
    try:
        pattern = rf"\b{_MONTH}(?:\s+(\d{{4}}))?\s+(?:to|through|thru|until|and|-)\s+{_MONTH}\s+(\d{{4}})\b"
        match = re.search(pattern, text)
        if not match:
            return None
        end_year = int(match.group(4))
        start_year = int(match.group(2)) if match.group(2) else end_year
        start = month_bounds(start_year, MONTHS[match.group(1)])[0]
        end = month_bounds(end_year, MONTHS[match.group(3)])[1]
        return (start, end) if start <= end else None
    except Exception as exc:
        logger.error("_month_range failed: %s", exc)
        raise


def _ordinal_quarter(text: str, today: date) -> Period | None:
    """
    #Feature: Date parsing
    #Scenario: "the second quarter of 2026"
    #Complexity: Time O(n)
    """
    try:
        ordinals = {"first": 1, "1st": 1, "second": 2, "2nd": 2, "third": 3, "3rd": 3, "fourth": 4, "4th": 4}
        match = re.search(r"\b(first|1st|second|2nd|third|3rd|fourth|4th) quarter (?:of )?(\d{4})\b", text)
        return quarter_bounds(int(match.group(2)), ordinals[match.group(1)]) if match else None
    except Exception as exc:
        logger.error("_ordinal_quarter failed: %s", exc)
        raise


def _month_name(text: str, today: date) -> Period | None:
    """
    #Feature: Date parsing
    #Scenario: "March 2024", or "March" alone meaning its most recent completed occurrence
    #Complexity: Time O(n)
    """
    try:
        match = re.search(rf"\b{_MONTH}(?:\s+(\d{{4}}))?\b", text)
        if not match:
            return None
        month = MONTHS[match.group(1)]
        if match.group(1) == "may" and not match.group(2):
            return None
        if match.group(2):
            return month_bounds(int(match.group(2)), month)
        year = today.year if month < today.month else today.year - 1
        return month_bounds(year, month)
    except Exception as exc:
        logger.error("_month_name failed: %s", exc)
        raise


def _year(text: str, today: date) -> Period | None:
    """
    #Feature: Date parsing
    #Scenario: "in 2024"
    #Complexity: Time O(n)
    """
    try:
        match = re.search(r"\b(20\d{2})\b", text)
        return (date(int(match.group(1)), 1, 1), date(int(match.group(1)), 12, 31)) if match else None
    except Exception as exc:
        logger.error("_year failed: %s", exc)
        raise


_PARSERS: list[Callable[[str, date], Period | None]] = [
    _explicit_range, _week_of, _last_n, _relative, _month_range, _quarter, _ordinal_quarter, _month_name,
    _single_day, _year,
]


def parse_period(text: str, today: date) -> Period | None:
    """
    #Feature: Date parsing
    #Scenario: Find the first time period mentioned in a question, most specific pattern first
    #Complexity: Time O(patterns * n)

    Args:
        text: Lower-cased question.
        today: The workspace "today".

    Returns:
        Inclusive (start, end), or None when no period is mentioned.

    Raises:
        ValueError: When text or today is None.
    """
    try:
        if text is None or today is None:
            raise ValueError("[parse_period] 'text' and 'today' are required.")
        return next((p for p in (parser(text, today) for parser in _PARSERS) if p), None)
    except Exception as exc:
        logger.error("parse_period failed: %s", exc)
        raise
