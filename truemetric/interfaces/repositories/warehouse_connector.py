from abc import ABC, abstractmethod
from typing import Any


class IWarehouseConnector(ABC):
    """
    #Feature: Warehouse connectors
    #Scenario: Read-only access to one customer warehouse
    #Complexity: Time O(1) per call, plus query cost
    """

    @abstractmethod
    def execute(self, sql: str, params: list[Any] | None = None) -> tuple[list[str], list[tuple]]:
        """
        #Feature: Warehouse connectors
        #Scenario: Run one read-only SELECT and return columns and rows
        #Complexity: Time O(query)

        Args:
            sql: A single SELECT statement.
            params: Positional bind parameters.

        Returns:
            Tuple of (column names, rows).

        Raises:
            Errors.Misc.UnsafeQuery: When sql is not a single read-only SELECT.
            Errors.Misc.QueryLimitExceeded: When the result exceeds the row cap.
        """

    @abstractmethod
    def table_columns(self, table: str) -> dict[str, str]:
        """
        #Feature: Warehouse connectors
        #Scenario: Read a table's columns and types from the catalog
        #Complexity: Time O(c) - c columns

        Args:
            table: Mart table name, unqualified.

        Returns:
            Mapping of column name to data type; empty when the table is missing.
        """

    @abstractmethod
    def qualify(self, table: str) -> str:
        """
        #Feature: Warehouse connectors
        #Scenario: Fully qualify and quote a mart table name
        #Complexity: Time O(n)

        Args:
            table: Unqualified table name.

        Returns:
            Quoted schema.table.

        Raises:
            ValueError: When table is not a plain identifier.
        """
