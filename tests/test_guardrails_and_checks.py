from datetime import datetime, timedelta
from pathlib import Path

import duckdb
import pytest

from truemetric.connectors import DuckDBConnector, assert_read_only
from truemetric.errors import Errors
from truemetric.schemas import ChecksConfig
from truemetric.services import WarehouseDataChecks

NOW = datetime(2026, 11, 1)


@pytest.mark.parametrize("sql", ["drop table x", "select 1; drop table x", "insert into x values (1)",
                                 "update x set a = 1", "copy x to 'out.csv'"])
def test_rejects_non_select(sql: str) -> None:
    """
    #Feature: Warehouse guardrails
    #Scenario: Only a single SELECT/WITH may run
    #Complexity: Time O(1)
    """
    with pytest.raises(Errors.Misc.UnsafeQuery):
        assert_read_only(sql)


def test_allows_select_with_comments() -> None:
    """
    #Feature: Warehouse guardrails
    #Scenario: MetricFlow SQL starts with comments and may end in a semicolon
    #Complexity: Time O(1)
    """
    assert assert_read_only("-- compiled\nwith a as (select 1) select * from a;").endswith("from a")


@pytest.fixture
def warehouse(tmp_path: Path) -> Path:
    """
    #Feature: Test fixtures
    #Scenario: Tiny mart with 40 days of 10 rows/day
    #Complexity: Time O(rows)
    """
    path = tmp_path / "warehouse.duckdb"
    with duckdb.connect(str(path)) as con:
        con.execute("create schema analytics")
        con.execute("create table analytics.facts (id integer, created_at timestamp, price double)")
        rows = [(d * 10 + i, NOW - timedelta(days=d, hours=1 + i), 50.0) for d in range(40) for i in range(10)]
        con.executemany("insert into analytics.facts values (?, ?, ?)", rows)
    return path


def checks_for(path: Path) -> WarehouseDataChecks:
    """
    #Feature: Test fixtures
    #Scenario: Checks wired to the tiny mart
    #Complexity: Time O(1)
    """
    config = ChecksConfig.model_validate({"tables": {"facts": {
        "timestamp_column": "created_at", "freshness_hours": 24, "unique_key": "id",
        "required_columns": ["id", "created_at", "price"], "not_null_columns": ["price"],
        "volume": {"min_ratio": 0.3, "max_ratio": 3.0},
        "distribution": {"column": "price", "min_ratio": 0.5, "max_ratio": 2.0}}}})
    return WarehouseDataChecks(DuckDBConnector(path, "analytics", 1000, "test"), config, lambda: NOW, "test", 0)


def mutate(path: Path, sql: str) -> None:
    """
    #Feature: Test fixtures
    #Scenario: Plant a fault
    #Complexity: Time O(rows)
    """
    with duckdb.connect(str(path)) as con:
        con.execute(sql)


def test_clean_table_passes(warehouse: Path) -> None:
    """
    #Feature: Data health checks
    #Scenario: Healthy data passes every check
    #Complexity: Time O(rows)
    """
    run = checks_for(warehouse).run_checks(["facts"])
    assert run.passed, run.failures


@pytest.mark.parametrize("sql,check", [
    ("delete from analytics.facts where created_at >= timestamp '2026-10-30 12:00'", "freshness"),
    ("insert into analytics.facts select * from analytics.facts where created_at >= timestamp '2026-10-31'",
     "unique"),
    ("alter table analytics.facts rename column price to price_usd", "schema"),
    ("update analytics.facts set price = null where id < 5", "not_null"),
    ("update analytics.facts set price = price * 100 where created_at >= timestamp '2026-10-25'", "distribution"),
])
def test_each_fault_is_caught(warehouse: Path, sql: str, check: str) -> None:
    """
    #Feature: Data health checks
    #Scenario: Each planted fault fails the matching check
    #Complexity: Time O(rows)
    """
    mutate(warehouse, sql)
    run = checks_for(warehouse).run_checks(["facts"])
    assert check in {f.check for f in run.failures}


def test_unconfigured_table_fails_closed(warehouse: Path) -> None:
    """
    #Feature: Data health checks
    #Scenario: A table with no configured checks is not trusted
    #Complexity: Time O(1)
    """
    assert not checks_for(warehouse).run_checks(["unknown_table"]).passed
