import logging
import re
from pathlib import Path
from typing import Any

import duckdb

from truemetric.errors import Errors
from truemetric.interfaces import IWarehouseConnector
from truemetric.utilities.sql import quote_identifier
from truemetric.utilities.validation import require

logger = logging.getLogger(__name__)

_SELECT = re.compile(r"^\s*(--[^\n]*\n\s*)*(select|with)\b", re.IGNORECASE)


def assert_read_only(sql: str) -> str:
    """
    #Feature: Warehouse guardrails
    #Scenario: Reject anything but a single SELECT/WITH statement
    #Complexity: Time O(n) - length of sql

    Args:
        sql: Candidate statement.

    Returns:
        The statement without a trailing semicolon.

    Raises:
        ValueError: When sql is None.
        Errors.Misc.UnsafeQuery: When sql is not a single read-only SELECT.
    """
    try:
        if sql is None:
            raise ValueError("[assert_read_only] 'sql' is required. Fix: pass a SELECT statement.")
        statement = sql.strip().rstrip(";")
        if not _SELECT.match(statement) or ";" in statement:
            raise Errors.Misc.UnsafeQuery(
                "[assert_read_only] Refused to run SQL. Invariant violated: only one SELECT/WITH statement "
                f"is allowed. Received: {statement[:80]!r}. Fix: send a single read-only SELECT."
            )
        return statement
    except Exception as exc:
        logger.warning("assert_read_only rejected sql: %s", exc)
        raise


class DuckDBConnector(IWarehouseConnector):
    """
    #Feature: Warehouse connectors
    #Scenario: Read-only DuckDB warehouse for local development, CI and evals
    #Complexity: Time O(query)

    Opens a fresh read-only connection per call so dbt can write between questions.
    """

    def __init__(self, path: Path, schema: str, max_rows: int, workspace_id: str) -> None:
        """
        #Feature: Warehouse connectors
        #Scenario: Bind the connector to one workspace's DuckDB file
        #Complexity: Time O(1)

        Args:
            path: DuckDB file.
            schema: Schema holding the marts.
            max_rows: Result row cap.
            workspace_id: Tenant id for logs.

        Raises:
            ValueError: When the DuckDB file does not exist.
        """
        try:
            if not Path(path).exists():
                raise ValueError(
                    f"[DuckDBConnector.__init__] Warehouse file not found: {path}. "
                    "Fix: run scripts/generate_thelook.py and dbt build first."
                )
            self._path, self._schema, self._max_rows, self._workspace_id = str(path), schema, max_rows, workspace_id
        except Exception as exc:
            logger.error("DuckDBConnector init failed: %s", exc, extra={"tenant_id": workspace_id})
            raise

    def execute(self, sql: str, params: list[Any] | None = None) -> tuple[list[str], list[tuple]]:
        """
        #Feature: Warehouse connectors
        #Scenario: Run one read-only SELECT on a fresh read-only connection, capped at max_rows
        #Complexity: Time O(query)

        Args:
            sql: A single SELECT/WITH statement.
            params: Positional bind parameters.

        Returns:
            (column names, rows).

        Raises:
            ValueError: When sql is None.
            Errors.Misc.UnsafeQuery: When sql is not a single read-only SELECT.
            Errors.Misc.QueryLimitExceeded: When the result exceeds the row cap.
        """
        try:
            statement = assert_read_only(sql)
            with duckdb.connect(self._path, read_only=True) as con:
                cursor = con.execute(statement, params or [])
                columns = [d[0] for d in cursor.description]
                rows = cursor.fetchmany(self._max_rows + 1)
            if len(rows) > self._max_rows:
                raise Errors.Misc.QueryLimitExceeded(
                    f"[DuckDBConnector.execute] Result exceeded {self._max_rows} rows. Invariant violated: results "
                    "stay under the workspace row cap. Fix: aggregate further or add a limit."
                )
            return columns, rows
        except Exception as exc:
            logger.error("execute failed: %s", exc, extra={"tenant_id": self._workspace_id})
            raise

    def table_columns(self, table: str) -> dict[str, str]:
        """
        #Feature: Warehouse connectors
        #Scenario: Read a mart's columns and types from information_schema
        #Complexity: Time O(columns)

        Args:
            table: Unqualified table name.

        Returns:
            Column name to data type; empty when the table is missing.

        Raises:
            ValueError: When table is None.
        """
        try:
            require("DuckDBConnector.table_columns", table=(table, str))
            _, rows = self.execute(
                "select column_name, data_type from information_schema.columns "
                "where table_schema = ? and table_name = ? order by ordinal_position",
                [self._schema, table],
            )
            return {name: dtype for name, dtype in rows}
        except Exception as exc:
            logger.error("table_columns failed for table=%s: %s", table, exc, extra={"tenant_id": self._workspace_id})
            raise

    def qualify(self, table: str) -> str:
        """
        #Feature: Warehouse connectors
        #Scenario: Fully qualify a mart table name after validating it as an identifier
        #Complexity: Time O(n)

        Args:
            table: Unqualified table name.

        Returns:
            Quoted schema.table.

        Raises:
            ValueError: When table is not a plain identifier.
        """
        try:
            return f"{quote_identifier(self._schema)}.{quote_identifier(table)}"
        except Exception as exc:
            logger.error("qualify failed: %s", exc, extra={"tenant_id": self._workspace_id})
            raise
