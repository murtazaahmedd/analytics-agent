import functools
import logging
from collections.abc import Callable
from typing import Any

from mcp.server.mcpserver.exceptions import ToolError

from truemetric.errors import TrueMetricError

logger = logging.getLogger(__name__)


def domain_errors(fn: Callable[..., Any]) -> Callable[..., Any]:
    """
    #Feature: MCP tool servers
    #Scenario: Return TrueMetric's descriptive errors to the MCP client instead of a generic failure
    #Complexity: Time O(1) overhead

    Args:
        fn: Tool function.

    Returns:
        Wrapped tool function that re-raises domain and validation errors as ToolError.
    """
    try:
        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            """
            #Feature: MCP tool servers
            #Scenario: Call the tool and translate domain errors
            #Complexity: Time O(tool)
            """
            try:
                return fn(*args, **kwargs)
            except (TrueMetricError, ValueError, TypeError) as exc:
                logger.warning("tool %s refused: %s", fn.__name__, exc)
                raise ToolError(str(exc)) from exc

        return wrapper
    except Exception as exc:
        logger.error("domain_errors failed: %s", exc)
        raise
