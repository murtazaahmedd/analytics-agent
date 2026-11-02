import logging
from typing import Any

from mcp.server.mcpserver import MCPServer

from truemetric.interfaces import IDataChecks
from truemetric.mcp_servers.tool_errors import domain_errors

logger = logging.getLogger(__name__)


def register_run_checks(server: MCPServer, checks: IDataChecks) -> None:
    """
    #Feature: MCP tool servers
    #Scenario: Register the run_checks tool
    #Complexity: Time O(1)

    Args:
        server: Server to register on.
        checks: Service the tool calls.
    """
    try:
        @server.tool(description="Run every configured check on the given mart tables. Unconfigured tables fail.")
        @domain_errors
        def run_checks(tables: list[str]) -> dict[str, Any]:
            """
            #Feature: MCP tool servers
            #Scenario: Run checks on mart tables
            #Complexity: Time O(tables * checks)
            """
            try:
                run = checks.run_checks(tables)
                return {"passed": run.passed, **run.model_dump(mode="json")}
            except Exception as exc:
                logger.warning("run_checks tool failed: %s", exc)
                raise
    except Exception as exc:
        logger.error("register_run_checks failed: %s", exc)
        raise


def register_get_last_run(server: MCPServer, checks: IDataChecks) -> None:
    """
    #Feature: MCP tool servers
    #Scenario: Register the get_last_run tool
    #Complexity: Time O(1)

    Args:
        server: Server to register on.
        checks: Service the tool calls.
    """
    try:
        @server.tool(description="The most recent check run, or null.")
        @domain_errors
        def get_last_run() -> dict[str, Any] | None:
            """
            #Feature: MCP tool servers
            #Scenario: Last check run for the data health page
            #Complexity: Time O(1)
            """
            try:
                run = checks.get_last_run()
                return {"passed": run.passed, **run.model_dump(mode="json")} if run else None
            except Exception as exc:
                logger.warning("get_last_run tool failed: %s", exc)
                raise
    except Exception as exc:
        logger.error("register_get_last_run failed: %s", exc)
        raise


def create_server(checks: IDataChecks) -> MCPServer:
    """
    #Feature: MCP tool servers
    #Scenario: Data checks server - freshness, volume, schema, nulls, uniqueness, distribution
    #Complexity: Time O(1) to build

    Args:
        checks: Workspace data checks.

    Returns:
        MCPServer exposing run_checks and get_last_run.
    """
    try:
        server = MCPServer("truemetric-checks", instructions="Run data health checks before trusting a table.")
        register_run_checks(server, checks)
        register_get_last_run(server, checks)
        return server
    except Exception as exc:
        logger.error("create_server failed: %s", exc)
        raise
