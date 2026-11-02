from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from truemetric.errors import Errors
from truemetric.utilities import bearer_token, naive_utc, resolve_inside, translate_db_error


def test_bearer_token_parsing() -> None:
    """
    #Feature: Authentication
    #Scenario: Only "Bearer <token>" headers yield a token
    #Complexity: Time O(1)
    """
    assert bearer_token("Bearer abc") == "abc" and bearer_token("bearer abc ") == "abc"
    assert bearer_token(None) is None and bearer_token("Basic abc") is None and bearer_token("Bearer ") is None


def test_naive_utc() -> None:
    """
    #Feature: Workspaces
    #Scenario: Aware clocks become naive UTC; naive clocks are left alone
    #Complexity: Time O(1)
    """
    karachi = timezone(timedelta(hours=5))
    assert naive_utc(datetime(2026, 11, 1, 5, tzinfo=karachi)) == datetime(2026, 11, 1)
    assert naive_utc(datetime(2026, 11, 1)) == datetime(2026, 11, 1) and naive_utc(None) is None


def test_resolve_inside(root: Path) -> None:
    """
    #Feature: Workspaces
    #Scenario: Paths must exist under the root; traversal and absolute escapes are refused
    #Complexity: Time O(1)
    """
    assert resolve_inside("demo_workspaces/thelook", root) == root / "demo_workspaces/thelook"
    for bad in ["../", "/etc", "demo_workspaces/../../", "missing_dir"]:
        with pytest.raises(Errors.HTTP.BadRequest):
            resolve_inside(bad, root)


def test_translate_db_error_maps_sqlstate() -> None:
    """
    #Feature: Control-plane database
    #Scenario: UDF SQLSTATEs map to domain errors; unknown ones pass through
    #Complexity: Time O(1)
    """
    class DriverError(Exception):
        def __init__(self, message: str, sqlstate: str) -> None:
            super().__init__(message)
            self.sqlstate = sqlstate

    assert isinstance(translate_db_error(DriverError("no", "TM403"), "t"), Errors.HTTP.Forbidden)
    assert isinstance(translate_db_error(DriverError("dup", "23505"), "t"), Errors.Database.IntegrityError)
    assert isinstance(translate_db_error(DriverError("slow", "TM429"), "t"), Errors.Misc.RateLimitExceeded)
    original = DriverError("other", "XX000")
    assert translate_db_error(original, "t") is original
