from abc import ABC, abstractmethod

from truemetric.schemas import FreshnessResult, SqlResult, TableProfile


class IWarehouseTools(ABC):
    """
    #Feature: Warehouse tools
    #Scenario: Profiling and checks; output is never shown as an answer
    #Complexity: Time O(1) per call, plus query cost
    """

    @abstractmethod
    def profile_table(self, table: str) -> TableProfile:
        """
        #Feature: Warehouse tools
        #Scenario: Row count and per-column null and distinct counts
        #Complexity: Time O(rows * columns)

        Args:
            table: Mart table name.

        Returns:
            TableProfile.
        """

    @abstractmethod
    def check_freshness(self, table: str, timestamp_column: str) -> FreshnessResult:
        """
        #Feature: Warehouse tools
        #Scenario: Newest timestamp in a table
        #Complexity: Time O(rows)

        Args:
            table: Mart table name.
            timestamp_column: Column holding event time.

        Returns:
            FreshnessResult.
        """

    @abstractmethod
    def run_sql_readonly(self, sql: str) -> SqlResult:
        """
        #Feature: Warehouse tools
        #Scenario: Ad-hoc read-only SQL for drafting and checks
        #Complexity: Time O(query)

        Args:
            sql: A single SELECT statement.

        Returns:
            SqlResult.
        """
