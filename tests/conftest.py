from datetime import datetime
from pathlib import Path

import pytest

from truemetric.schemas import MetricInfo

ROOT = Path(__file__).resolve().parents[1]
WAREHOUSE = ROOT / "data" / "warehouse.duckdb"


@pytest.fixture(scope="session")
def root() -> Path:
    """
    #Feature: Test fixtures
    #Scenario: Repository root
    #Complexity: Time O(1)
    """
    return ROOT


@pytest.fixture(scope="session")
def warehouse_path() -> Path:
    """
    #Feature: Test fixtures
    #Scenario: Demo warehouse; integration tests skip when it has not been built
    #Complexity: Time O(1)
    """
    if not WAREHOUSE.exists():
        pytest.skip("run `make data` first")
    return WAREHOUSE


@pytest.fixture
def catalog() -> list[MetricInfo]:
    """
    #Feature: Test fixtures
    #Scenario: A small metric catalog without a warehouse
    #Complexity: Time O(1)
    """
    dims = ["user__country", "user__traffic_source", "product__category", "product__brand"]
    return [
        MetricInfo(name="gross_revenue", label="Gross revenue", description="Sum of sale price.", unit="currency",
                   dimensions=dims, tables=["fct_order_items"]),
        MetricInfo(name="net_revenue", label="Net revenue", description="Gross minus returns.", unit="currency",
                   dimensions=dims, tables=["fct_order_items"]),
        MetricInfo(name="units_sold", label="Units sold", description="Items sold.", unit="count",
                   dimensions=dims, tables=["fct_order_items"]),
        MetricInfo(name="sessions", label="Sessions", description="Web sessions.", unit="count",
                   dimensions=["session__browser", "session__traffic_source", "user__country"],
                   tables=["fct_sessions"]),
    ]


@pytest.fixture
def values() -> dict[str, list[str]]:
    """
    #Feature: Test fixtures
    #Scenario: Known dimension values for filter matching
    #Complexity: Time O(1)
    """
    return {"country": ["Brasil", "United States", "China"], "browser": ["Safari", "Chrome"],
            "category": ["Jeans", "Swim"], "status": ["Complete", "Returned"]}


@pytest.fixture
def as_of() -> datetime:
    """
    #Feature: Test fixtures
    #Scenario: Pinned workspace clock
    #Complexity: Time O(1)
    """
    return datetime(2026, 11, 1)
