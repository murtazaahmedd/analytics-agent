import logging

from truemetric.constants import LLM_MAX_TOKENS, LLM_NUM_RETRIES
from truemetric.interfaces import Completion
from truemetric.schemas import LLMSettings

logger = logging.getLogger(__name__)


def litellm_completion(settings: LLMSettings) -> Completion:
    """
    #Feature: LLM routing
    #Scenario: LiteLLM-backed completion with fallback models, retries and deterministic sampling
    #Complexity: Time O(1) plus model latency

    Args:
        settings: Model, fallbacks, reasoning effort and timeout.

    Returns:
        Completion function taking chat messages and returning the reply text.
    """
    try:
        import litellm

        extra = {"reasoning_effort": settings.reasoning_effort} if settings.reasoning_effort else {}

        def complete(messages: list[dict[str, str]]) -> str:
            """
            #Feature: LLM routing
            #Scenario: One routing call to the configured model
            #Complexity: Time O(1) plus model latency

            Args:
                messages: Chat messages.

            Returns:
                Reply text.
            """
            try:
                response = litellm.completion(model=settings.model, messages=messages, temperature=0,
                                              max_tokens=LLM_MAX_TOKENS, fallbacks=settings.fallbacks or None,
                                              timeout=settings.timeout_seconds, num_retries=LLM_NUM_RETRIES, **extra)
                return response.choices[0].message.content
            except Exception as exc:
                logger.warning("LLM call failed for model=%s: %s", settings.model, exc)
                raise

        return complete
    except Exception as exc:
        logger.error("litellm_completion failed for model=%s: %s", settings.model, exc)
        raise
