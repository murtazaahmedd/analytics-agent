import logging
from datetime import date
from typing import Any

from mcp.server.mcpserver import MCPServer

from truemetric.interfaces import ISemanticLayer
from truemetric.mcp_servers.tool_errors import domain_errors
from truemetric.schemas import Grain, MetricFilter, MetricQuery

logger = logging.getLogger(__name__)


def register_list_metrics(server: MCPServer, semantic: ISemanticLayer) -> None:
    """
    #Feature: MCP tool servers
    #Scenario: Register the list_metrics tool
    #Complexity: Time O(1)

    Args:
        server: Server to register on.
        semantic: Service the tool calls.
    """
    try:
        @server.tool(description="List approved metrics with descriptions, units and available dimensions.")
        @domain_errors
        def list_metrics() -> list[dict[str, Any]]:
            """
            #Feature: MCP tool servers
            #Scenario: Catalog of approved metrics
            #Complexity: Time O(metrics)
            """
            try:
                return [m.model_dump() for m in semantic.list_metrics()]
            except Exception as exc:
                logger.warning("list_metrics tool failed: %s", exc)
                raise
    except Exception as exc:
        logger.error("register_list_metrics failed: %s", exc)
        raise


def register_describe_metric(server: MCPServer, semantic: ISemanticLayer) -> None:
    """
    #Feature: MCP tool servers
    #Scenario: Register the describe_metric tool
    #Complexity: Time O(1)

    Args:
        server: Server to register on.
        semantic: Service the tool calls.
    """
    try:
        @server.tool(description="Definition, unit, dimensions and backing tables of one metric.")
        @domain_errors
        def describe_metric(name: str) -> dict[str, Any]:
            """
            #Feature: MCP tool servers
            #Scenario: One metric's definition
            #Complexity: Time O(1)
            """
            try:
                return semantic.describe_metric(name).model_dump()
            except Exception as exc:
                logger.warning("describe_metric tool failed: %s", exc)
                raise
    except Exception as exc:
        logger.error("register_describe_metric failed: %s", exc)
        raise


def register_query_metric(server: MCPServer, semantic: ISemanticLayer) -> None:
    """
    #Feature: MCP tool servers
    #Scenario: Register the query_metric tool
    #Complexity: Time O(1)

    Args:
        server: Server to register on.
        semantic: Service the tool calls.
    """
    try:
        @server.tool(description="Query one metric. Dates are inclusive. Dimensions may be short (country) "
                                 "or qualified (user__country).")
        @domain_errors
        def query_metric(metric: str, group_by: list[str] | None = None, filters: list[MetricFilter] | None = None,
                         grain: Grain | None = None, start: date | None = None, end: date | None = None,
                         order: str | None = None, limit: int | None = None) -> dict[str, Any]:
            """
            #Feature: MCP tool servers
            #Scenario: Compile and run a metric query through MetricFlow
            #Complexity: Time O(query)
            """
            try:
                query = MetricQuery(metric=metric, group_by=group_by or [], filters=filters or [], grain=grain,
                                    start=start, end=end, order=order, limit=limit)
                return semantic.query_metric(query).model_dump(mode="json")
            except Exception as exc:
                logger.warning("query_metric tool failed: %s", exc)
                raise
    except Exception as exc:
        logger.error("register_query_metric failed: %s", exc)
        raise


def create_server(semantic: ISemanticLayer) -> MCPServer:
    """
    #Feature: MCP tool servers
    #Scenario: Semantic layer server - the only path to a number shown to a user
    #Complexity: Time O(1) to build

    Args:
        semantic: Workspace semantic layer.

    Returns:
        MCPServer exposing list_metrics, describe_metric and query_metric.
    """
    try:
        server = MCPServer("truemetric-semantic-layer",
                           instructions="Answer metric questions only through these tools. Never compute numbers.")
        register_list_metrics(server, semantic)
        register_describe_metric(server, semantic)
        register_query_metric(server, semantic)
        return server
    except Exception as exc:
        logger.error("create_server failed: %s", exc)
        raise
