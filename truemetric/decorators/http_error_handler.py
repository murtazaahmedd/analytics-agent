import logging
from collections.abc import Awaitable, Callable
from functools import wraps
from typing import Any

from fastapi.responses import JSONResponse

from truemetric.errors import Errors

logger = logging.getLogger(__name__)

_STATUS: list[tuple[type[Exception], int]] = [
    (Errors.HTTP.BadRequest, 400),
    (Errors.HTTP.Unauthorized, 401),
    (Errors.HTTP.Forbidden, 403),
    (Errors.HTTP.NotFound, 404),
    (Errors.Database.IntegrityError, 409),
    (Errors.Misc.RateLimitExceeded, 429),
]


def error_response(exc: Exception) -> JSONResponse:
    """
    #Feature: HTTP errors
    #Scenario: Map a domain error to a status code; anything unexpected is a 500 with no internals leaked
    #Complexity: Time O(mapped errors)

    Args:
        exc: Raised exception.

    Returns:
        JSON error response.
    """
    try:
        for error_type, status in _STATUS:
            if isinstance(exc, error_type):
                headers = {"WWW-Authenticate": "Bearer"} if status == 401 else None
                return JSONResponse({"detail": str(exc)}, status_code=status, headers=headers)
        logger.exception("unhandled error", exc_info=exc)
        return JSONResponse({"detail": "Internal error. The request was not completed."}, status_code=500)
    except Exception as err:
        logger.error("error_response failed: %s", err)
        raise


def http_error_handler(func: Callable[..., Awaitable[Any]]) -> Callable[..., Awaitable[Any]]:
    """
    #Feature: HTTP errors
    #Scenario: Outer decorator on every endpoint (below @router.*, above @enforce)
    #Complexity: Time O(1) overhead

    Args:
        func: Endpoint coroutine.

    Returns:
        Wrapped endpoint that turns exceptions into JSON error responses.
    """

    @wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        """
        #Feature: HTTP errors
        #Scenario: Run the endpoint, convert failures
        #Complexity: Time O(endpoint)
        """
        try:
            return await func(*args, **kwargs)
        except Exception as exc:
            return error_response(exc)

    return wrapper
