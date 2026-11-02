from abc import ABC, abstractmethod

from truemetric.schemas import CheckRun


class IDataChecks(ABC):
    """
    #Feature: Data health checks
    #Scenario: Freshness, volume, schema, null, uniqueness and distribution checks
    #Complexity: Time O(tables * checks)
    """

    @abstractmethod
    def run_checks(self, tables: list[str]) -> CheckRun:
        """
        #Feature: Data health checks
        #Scenario: Run every configured check on the given marts
        #Complexity: Time O(tables * checks)

        Args:
            tables: Mart table names; unconfigured tables fail closed.

        Returns:
            The run with one result per check.
        """

    @abstractmethod
    def get_last_run(self) -> CheckRun | None:
        """
        #Feature: Data health checks
        #Scenario: Most recent run, for the data health page
        #Complexity: Time O(1)

        Returns:
            The last run, or None if no checks have run.
        """
