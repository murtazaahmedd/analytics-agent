import logging
from collections.abc import Awaitable, Callable
from functools import wraps
from typing import Any

from truemetric.utilities import bearer_token

logger = logging.getLogger(__name__)


def enforce(permission: str) -> Callable[[Callable[..., Awaitable[Any]]], Callable[..., Awaitable[Any]]]:
    """
    #Feature: Access control
    #Scenario: Innermost endpoint decorator - authenticate, rate-limit, RBAC, bind row-level security
    #Complexity: Time O(1) per request

    The endpoint must take `request: Request` and `services` (ControlPlaneServiceContainer) parameters, and a
    `workspace_id` path parameter when the permission is workspace-scoped. On success request.state.auth holds
    the AuthContext.

    Args:
        permission: resource.action permission from utilities.auth_reforce.

    Returns:
        Decorator.

    Raises:
        ValueError: When permission is None.
    """
    if permission is None:
        raise ValueError("[enforce] 'permission' is required. Fix: pass a constant from utilities.auth_reforce.")

    def decorator(func: Callable[..., Awaitable[Any]]) -> Callable[..., Awaitable[Any]]:
        """
        #Feature: Access control
        #Scenario: Wrap one endpoint
        #Complexity: Time O(1)
        """

        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            """
            #Feature: Access control
            #Scenario: Authorise, then call the endpoint
            #Complexity: Time O(1) plus the endpoint
            """
            request, services = kwargs.get("request"), kwargs.get("services")
            if request is None or services is None:
                raise ValueError(f"[enforce] Endpoint {func.__name__} must declare 'request' and 'services'.")
            try:
                token = bearer_token(request.headers.get("authorization"))
                request.state.auth = await services.auth.authorize(token, kwargs.get("workspace_id"), permission)
            except Exception as exc:
                logger.warning("enforce %s rejected: %s", permission, exc,
                               extra={"tenant_id": str(kwargs.get("workspace_id"))})
                raise
            return await func(*args, **kwargs)

        return wrapper

    return decorator
