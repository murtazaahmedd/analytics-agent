from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ColumnProfile(BaseModel):
    """
    #Feature: Warehouse tools
    #Scenario: Type, distinct and null counts for one column
    #Complexity: Time O(1)
    """

    name: str
    type: str
    distinct: int
    nulls: int


class TableProfile(BaseModel):
    """
    #Feature: Warehouse tools
    #Scenario: Profile of one mart table; exists is False when the table is missing
    #Complexity: Time O(1)
    """

    table: str
    exists: bool
    row_count: int | None = None
    columns: list[ColumnProfile] = Field(default_factory=list)


class FreshnessResult(BaseModel):
    """
    #Feature: Warehouse tools
    #Scenario: Newest timestamp in a table
    #Complexity: Time O(1)
    """

    table: str
    max_timestamp: datetime | None


class SqlResult(BaseModel):
    """
    #Feature: Warehouse tools
    #Scenario: Columns and rows of an ad-hoc read-only query
    #Complexity: Time O(1)
    """

    columns: list[str]
    rows: list[list[Any]]
