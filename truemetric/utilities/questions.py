import logging
import re

from truemetric.constants import GRAIN_WORDS, SERIES_WORDS

logger = logging.getLogger(__name__)


def asks_for_series(question: str) -> bool:
    """
    #Feature: Agent routing
    #Scenario: Whether a question asks for a time series ("by month", "weekly", "trend") rather than one total
    #Complexity: Time O(phrases * n)

    Args:
        question: The user's question.

    Returns:
        True when a grain or series phrase appears as whole words.

    Raises:
        ValueError: When question is None.
    """
    try:
        if question is None:
            raise ValueError("[asks_for_series] 'question' is required.")
        text = re.sub(r"[^a-z0-9]+", " ", question.lower())
        return any(re.search(rf"\b{re.escape(p)}\b", text) for p in [*GRAIN_WORDS, *SERIES_WORDS])
    except Exception as exc:
        logger.error("asks_for_series failed: %s", exc)
        raise
