import logging
from typing import Any

logger = logging.getLogger(__name__)


def require(owner: str, **arguments: tuple[Any, type | tuple[type, ...]]) -> None:
    """
    #Feature: Input validation
    #Scenario: None-check every required argument first, then type-check them (CLAUDE.md order)
    #Complexity: Time O(arguments)

    Args:
        owner: "Class.method" used in error messages.
        arguments: name=(value, expected type or tuple of types).

    Raises:
        ValueError: When any argument is None.
        TypeError: When a present argument has the wrong type.
    """
    try:
        for name, (value, _) in arguments.items():
            if value is None:
                raise ValueError(f"[{owner}] '{name}' is required and must not be None. Fix: pass a value.")
        for name, (value, expected) in arguments.items():
            if not isinstance(value, expected):
                raise TypeError(f"[{owner}] '{name}' must be {expected}, got {type(value).__name__}. "
                                "Fix: pass the expected type.")
    except Exception as exc:
        logger.warning("require failed: %s", exc)
        raise
