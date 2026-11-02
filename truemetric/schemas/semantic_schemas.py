from datetime import date
from typing import Any, Literal

from pydantic import BaseModel, Field

Grain = Literal["day", "week", "month", "quarter", "year"]


class MetricInfo(BaseModel):
    """
    #Feature: Semantic layer
    #Scenario: Public description of one approved metric
    #Complexity: Time O(1)
    """

    name: str
    label: str
    description: str
    unit: str = "number"
    dimensions: list[str] = Field(default_factory=list)
    tables: list[str] = Field(default_factory=list)


class MetricFilter(BaseModel):
    """
    #Feature: Semantic layer
    #Scenario: Equality filter on a categorical dimension
    #Complexity: Time O(1)
    """

    dimension: str = Field(min_length=1)
    values: list[str] = Field(min_length=1)


class MetricQuery(BaseModel):
    """
    #Feature: Semantic layer
    #Scenario: A structured request for one metric
    #Complexity: Time O(1)

    start and end are inclusive dates. order is "desc", "asc" or None.
    """

    metric: str = Field(min_length=1)
    group_by: list[str] = Field(default_factory=list)
    filters: list[MetricFilter] = Field(default_factory=list)
    grain: Grain | None = None
    start: date | None = None
    end: date | None = None
    order: Literal["desc", "asc"] | None = None
    limit: int | None = Field(default=None, ge=1, le=1000)


class MetricResult(BaseModel):
    """
    #Feature: Semantic layer
    #Scenario: Rows returned for a metric query, with the SQL that produced them
    #Complexity: Time O(1)
    """

    query: MetricQuery
    columns: list[str]
    rows: list[dict[str, Any]]
    sql: str
