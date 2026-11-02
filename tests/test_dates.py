from datetime import date

import pytest

from truemetric.utilities import parse_period

TODAY = date(2026, 11, 1)


@pytest.mark.parametrize("text,expected", [
    ("net revenue in march 2024", (date(2024, 3, 1), date(2024, 3, 31))),
    ("aov last quarter", (date(2026, 7, 1), date(2026, 9, 30))),
    ("sales last week", (date(2026, 10, 19), date(2026, 10, 25))),
    ("q3 2025", (date(2025, 7, 1), date(2025, 9, 30))),
    ("in 2024", (date(2024, 1, 1), date(2024, 12, 31))),
    ("last 7 days", (date(2026, 10, 25), date(2026, 10, 31))),
    ("yesterday", (date(2026, 10, 31), date(2026, 10, 31))),
    ("between 2024-01-01 and 2024-02-15", (date(2024, 1, 1), date(2024, 2, 15))),
    ("week of 2026-10-21", (date(2026, 10, 19), date(2026, 10, 25))),
    ("september", (date(2026, 9, 1), date(2026, 9, 30))),
    ("orders in may 2025", (date(2025, 5, 1), date(2025, 5, 31))),
    ("net revenue per month, january to march 2026", (date(2026, 1, 1), date(2026, 3, 31))),
    ("gross margin between july and september 2026", (date(2026, 7, 1), date(2026, 9, 30))),
    ("jan 2025 through mar 2026", (date(2025, 1, 1), date(2026, 3, 31))),
    ("the second quarter of 2026", (date(2026, 4, 1), date(2026, 6, 30))),
])
def test_parse_period(text: str, expected: tuple[date, date]) -> None:
    """
    #Feature: Date parsing
    #Scenario: Relative and absolute periods resolve to inclusive calendar ranges
    #Complexity: Time O(1)
    """
    assert parse_period(text, TODAY) == expected


@pytest.mark.parametrize("text", ["may i see orders", "top 5 countries", "net revenue"])
def test_no_period(text: str) -> None:
    """
    #Feature: Date parsing
    #Scenario: Words that look like dates do not create a period
    #Complexity: Time O(1)
    """
    assert parse_period(text, TODAY) is None
