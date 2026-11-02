import logging

from truemetric.interfaces import IWarehouseConnector, IWarehouseTools
from truemetric.schemas import ColumnProfile, FreshnessResult, SqlResult, TableProfile
from truemetric.utilities import quote_identifier, require, to_plain

logger = logging.getLogger(__name__)


class WarehouseTools(IWarehouseTools):
    """
    #Feature: Warehouse tools
    #Scenario: Read-only profiling for checks and metric drafting; never the source of an answer
    #Complexity: Time O(query)
    """

    def __init__(self, connector: IWarehouseConnector, workspace_id: str) -> None:
        """
        #Feature: Warehouse tools
        #Scenario: Bind tools to one workspace's read-only connector
        #Complexity: Time O(1)

        Args:
            connector: Read-only warehouse connector.
            workspace_id: Tenant id for logs.

        Raises:
            ValueError: When a dependency is None.
        """
        try:
            require("WarehouseTools.__init__", connector=(connector, IWarehouseConnector),
                    workspace_id=(workspace_id, str))
            self._connector, self._workspace_id = connector, workspace_id
        except Exception as exc:
            logger.error("WarehouseTools init failed: %s", exc, extra={"tenant_id": workspace_id})
            raise

    def profile_table(self, table: str) -> TableProfile:
        """
        #Feature: Warehouse tools
        #Scenario: Row count and per-column type, distinct and null counts
        #Complexity: Time O(rows * columns)

        Args:
            table: Mart table name.

        Returns:
            TableProfile; exists is False when the table is missing.

        Raises:
            ValueError: When table is None or not a plain identifier.
        """
        try:
            require("WarehouseTools.profile_table", table=(table, str))
            columns = self._connector.table_columns(table)
            if not columns:
                return TableProfile(table=table, exists=False)
            stats = ", ".join(f"count(distinct {quote_identifier(c)}), count(*) - count({quote_identifier(c)})"
                              for c in columns)
            row = self._connector.execute(f"select count(*), {stats} from {self._connector.qualify(table)}")[1][0]
            profile = [ColumnProfile(name=c, type=t, distinct=row[1 + 2 * i], nulls=row[2 + 2 * i])
                       for i, (c, t) in enumerate(columns.items())]
            return TableProfile(table=table, exists=True, row_count=row[0], columns=profile)
        except Exception as exc:
            logger.error("profile_table failed for table=%s: %s", table, exc, extra={"tenant_id": self._workspace_id})
            raise

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

        Raises:
            ValueError: When an argument is None or not a plain identifier.
        """
        try:
            require("WarehouseTools.check_freshness", table=(table, str), timestamp_column=(timestamp_column, str))
            _, rows = self._connector.execute(
                f"select max({quote_identifier(timestamp_column)}) from {self._connector.qualify(table)}")
            return FreshnessResult(table=table, max_timestamp=rows[0][0])
        except Exception as exc:
            logger.error("check_freshness failed for table=%s: %s", table, exc,
                         extra={"tenant_id": self._workspace_id})
            raise

    def run_sql_readonly(self, sql: str) -> SqlResult:
        """
        #Feature: Warehouse tools
        #Scenario: Ad-hoc read-only SQL for drafting and checks
        #Complexity: Time O(query)

        Args:
            sql: A single SELECT statement.

        Returns:
            SqlResult.

        Raises:
            ValueError: When sql is None.
            Errors.Misc.UnsafeQuery: When sql is not a single read-only SELECT.
        """
        try:
            require("WarehouseTools.run_sql_readonly", sql=(sql, str))
            columns, rows = self._connector.execute(sql)
            return SqlResult(columns=columns, rows=[[to_plain(v) for v in row] for row in rows])
        except Exception as exc:
            logger.error("run_sql_readonly failed: %s", exc, extra={"tenant_id": self._workspace_id})
            raise
