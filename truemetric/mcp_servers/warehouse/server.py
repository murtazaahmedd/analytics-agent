import logging
from typing import Any

from mcp.server.mcpserver import MCPServer

from truemetric.interfaces import IWarehouseTools
from truemetric.mcp_servers.tool_errors import domain_errors

logger = logging.getLogger(__name__)


def register_profile_table(server: MCPServer, warehouse: IWarehouseTools) -> None:
    """
    #Feature: MCP tool servers
    #Scenario: Register the profile_table tool
    #Complexity: Time O(1)

    Args:
        server: Server to register on.
        warehouse: Service the tool calls.
    """
    try:
        @server.tool(description="Row count and per-column type, distinct and null counts for a mart table.")
        @domain_errors
        def profile_table(table: str) -> dict[str, Any]:
            """
            #Feature: MCP tool servers
            #Scenario: Profile a mart table
            #Complexity: Time O(rows * columns)
            """
            try:
                return warehouse.profile_table(table).model_dump(mode="json")
            except Exception as exc:
                logger.warning("profile_table tool failed: %s", exc)
                raise
    except Exception as exc:
        logger.error("register_profile_table failed: %s", exc)
        raise


def register_check_freshness(server: MCPServer, warehouse: IWarehouseTools) -> None:
    """
    #Feature: MCP tool servers
    #Scenario: Register the check_freshness tool
    #Complexity: Time O(1)

    Args:
        server: Server to register on.
        warehouse: Service the tool calls.
    """
    try:
        @server.tool(description="Newest timestamp in a mart table.")
        @domain_errors
        def check_freshness(table: str, timestamp_column: str) -> dict[str, Any]:
            """
            #Feature: MCP tool servers
            #Scenario: Newest timestamp in a table
            #Complexity: Time O(rows)
            """
            try:
                return warehouse.check_freshness(table, timestamp_column).model_dump(mode="json")
            except Exception as exc:
                logger.warning("check_freshness tool failed: %s", exc)
                raise
    except Exception as exc:
        logger.error("register_check_freshness failed: %s", exc)
        raise


def register_run_sql_readonly(server: MCPServer, warehouse: IWarehouseTools) -> None:
    """
    #Feature: MCP tool servers
    #Scenario: Register the run_sql_readonly tool
    #Complexity: Time O(1)

    Args:
        server: Server to register on.
        warehouse: Service the tool calls.
    """
    try:
        @server.tool(description="Run one read-only SELECT. Anything else is rejected.")
        @domain_errors
        def run_sql_readonly(sql: str) -> dict[str, Any]:
            """
            #Feature: MCP tool servers
            #Scenario: Ad-hoc read-only SQL for drafting and checks
            #Complexity: Time O(query)
            """
            try:
                return warehouse.run_sql_readonly(sql).model_dump(mode="json")
            except Exception as exc:
                logger.warning("run_sql_readonly tool failed: %s", exc)
                raise
    except Exception as exc:
        logger.error("register_run_sql_readonly failed: %s", exc)
        raise


def create_server(warehouse: IWarehouseTools) -> MCPServer:
    """
    #Feature: MCP tool servers
    #Scenario: Read-only warehouse server for checks and drafting; output is never an answer
    #Complexity: Time O(1) to build

    Args:
        warehouse: Workspace warehouse tools.

    Returns:
        MCPServer exposing profile_table, check_freshness and run_sql_readonly.
    """
    try:
        server = MCPServer("truemetric-warehouse",
                           instructions="Read-only. Results are for profiling and drafting, never shown as answers.")
        register_profile_table(server, warehouse)
        register_check_freshness(server, warehouse)
        register_run_sql_readonly(server, warehouse)
        return server
    except Exception as exc:
        logger.error("create_server failed: %s", exc)
        raise
