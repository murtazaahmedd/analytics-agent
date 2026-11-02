import logging
from datetime import datetime

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class VolumeRule(BaseModel):
    """
    #Feature: Data health checks
    #Scenario: Allowed ratio of last complete day's rows to the trailing 7-day average
    #Complexity: Time O(1)
    """

    min_ratio: float = Field(gt=0)
    max_ratio: float = Field(gt=0)


class DistributionRule(BaseModel):
    """
    #Feature: Data health checks
    #Scenario: Allowed ratio of a column's 7-day mean to its prior 28-day mean
    #Complexity: Time O(1)
    """

    column: str = Field(min_length=1)
    min_ratio: float = Field(gt=0)
    max_ratio: float = Field(gt=0)


class TableCheckConfig(BaseModel):
    """
    #Feature: Data health checks
    #Scenario: Checks configured for one mart in truemetric_checks.yml
    #Complexity: Time O(1)
    """

    timestamp_column: str | None = None
    freshness_hours: float | None = Field(default=None, gt=0)
    unique_key: str | None = None
    required_columns: list[str] = Field(default_factory=list)
    not_null_columns: list[str] = Field(default_factory=list)
    volume: VolumeRule | None = None
    distribution: DistributionRule | None = None


class ChecksConfig(BaseModel):
    """
    #Feature: Data health checks
    #Scenario: All table checks for a workspace
    #Complexity: Time O(1)
    """

    tables: dict[str, TableCheckConfig]


class CheckResult(BaseModel):
    """
    #Feature: Data health checks
    #Scenario: Outcome of one check on one table
    #Complexity: Time O(1)
    """

    table: str
    check: str
    passed: bool
    detail: str


class CheckRun(BaseModel):
    """
    #Feature: Data health checks
    #Scenario: All check results for a set of tables at a point in time
    #Complexity: Time O(1)
    """

    ran_at: datetime
    results: list[CheckResult]

    @property
    def passed(self) -> bool:
        """
        #Feature: Data health checks
        #Scenario: A run passes only when every check passed
        #Complexity: Time O(n)

        Returns:
            True when all results passed.
        """
        try:
            return all(result.passed for result in self.results)
        except Exception as exc:
            logger.error("CheckRun.passed failed: %s", exc)
            raise

    @property
    def failures(self) -> list[CheckResult]:
        """
        #Feature: Data health checks
        #Scenario: List the failed checks for a blocked answer
        #Complexity: Time O(n)

        Returns:
            Failed results.
        """
        try:
            return [result for result in self.results if not result.passed]
        except Exception as exc:
            logger.error("CheckRun.failures failed: %s", exc)
            raise
