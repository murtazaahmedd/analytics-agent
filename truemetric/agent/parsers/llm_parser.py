import json
import logging
import re
from datetime import date

from pydantic import BaseModel, Field, field_validator

from truemetric.constants import ROUTER_SYSTEM_PROMPT, ROUTER_USER_PROMPT
from truemetric.interfaces import Completion, IQuestionParser
from truemetric.schemas import Grain, Intent, MetricFilter, MetricInfo, MetricQuery, ParsedQuestion

logger = logging.getLogger(__name__)


class RouterReply(BaseModel):
    """
    #Feature: LLM routing
    #Scenario: The JSON object the router model must return
    #Complexity: Time O(1)
    """

    intent: Intent
    metric: str | None = None
    group_by: list[str] = Field(default_factory=list)
    filters: list[MetricFilter] = Field(default_factory=list)
    grain: Grain | None = None
    start: date | None = None
    end: date | None = None
    order: str | None = None
    limit: int | None = Field(default=None, ge=1, le=1000)
    gap: str | None = None
    options: list[str] = Field(default_factory=list)

    @field_validator("group_by", "filters", "options", mode="before")
    @classmethod
    def null_as_empty(cls, value: object) -> object:
        """
        #Feature: LLM routing
        #Scenario: Models often send null for an empty list
        #Complexity: Time O(1)

        Args:
            value: Raw field value.

        Returns:
            [] for None, else the value.
        """
        try:
            return [] if value is None else value
        except Exception as exc:
            logger.error("null_as_empty failed: %s", exc)
            raise


def short_dimension(name: str) -> str:
    """
    #Feature: LLM routing
    #Scenario: user__country -> country, so the prompt stays short and the semantic layer resolves paths
    #Complexity: Time O(n)

    Args:
        name: Qualified dimension name.

    Returns:
        Last path segment.
    """
    try:
        return name.split("__")[-1]
    except Exception as exc:
        logger.error("short_dimension failed: %s", exc)
        raise


def render_catalog(catalog: list[MetricInfo]) -> str:
    """
    #Feature: LLM routing
    #Scenario: One line per metric for the router prompt
    #Complexity: Time O(m * d)

    Args:
        catalog: Approved metrics.

    Returns:
        Prompt text.
    """
    try:
        lines = []
        for metric in catalog:
            dims = ", ".join(sorted({short_dimension(d) for d in metric.dimensions}))
            lines.append(f"- {metric.name}: {metric.description} Dimensions: {dims}")
        return "\n".join(lines)
    except Exception as exc:
        logger.error("render_catalog failed: %s", exc)
        raise


def extract_json(text: str) -> dict:
    """
    #Feature: LLM routing
    #Scenario: Pull the first JSON object out of a model reply (tolerates code fences)
    #Complexity: Time O(n)

    Args:
        text: Model reply.

    Returns:
        Parsed object.

    Raises:
        ValueError: When no JSON object is present.
    """
    try:
        match = re.search(r"\{.*\}", text or "", re.DOTALL)
        if not match:
            raise ValueError(f"[extract_json] No JSON object in model reply: {text[:120]!r}. Fix: check the prompt.")
        return json.loads(match.group(0))
    except Exception as exc:
        logger.error("extract_json failed: %s", exc)
        raise


def to_parsed(reply: RouterReply, catalog: list[MetricInfo]) -> ParsedQuestion:
    """
    #Feature: LLM routing
    #Scenario: Convert the model reply, discarding any metric the catalog does not contain
    #Complexity: Time O(m)

    Args:
        reply: Validated model reply.
        catalog: Approved metrics.

    Returns:
        ParsedQuestion.
    """
    try:
        names = {m.name for m in catalog}
        options = [o for o in reply.options if o in names]
        if reply.intent in (Intent.WHAT, Intent.WHY) and reply.metric not in names:
            if reply.intent == Intent.WHY:
                return ParsedQuestion(intent=Intent.WHY, source="llm")
            return ParsedQuestion(intent=Intent.OUT_OF_SCOPE, gap=reply.gap or f"'{reply.metric}'", source="llm")
        if reply.intent != Intent.WHAT:
            query = MetricQuery(metric=reply.metric) if reply.metric in names else None
            return ParsedQuestion(intent=reply.intent, query=query, gap=reply.gap, options=options, source="llm")
        order = reply.order if reply.order in ("asc", "desc") else None
        query = MetricQuery(metric=reply.metric, group_by=reply.group_by, filters=reply.filters, grain=reply.grain,
                            start=reply.start, end=reply.end, order=order, limit=reply.limit)
        return ParsedQuestion(intent=Intent.WHAT, query=query, source="llm")
    except Exception as exc:
        logger.error("to_parsed failed: %s", exc)
        raise


class LLMQuestionParser(IQuestionParser):
    """
    #Feature: LLM routing
    #Scenario: Model-based routing through an injected completion function, with a deterministic fallback
    #Complexity: Time O(1) plus model latency
    """

    def __init__(self, complete: Completion, fallback: IQuestionParser) -> None:
        """
        #Feature: LLM routing
        #Scenario: Inject the model call and the fallback parser
        #Complexity: Time O(1)

        Args:
            complete: Takes chat messages, returns the reply text (LiteLLM in production, a fake in tests).
            fallback: Used when the model call or its reply fails validation.
        """
        try:
            self._complete, self._fallback = complete, fallback
        except Exception as exc:
            logger.error("LLMQuestionParser init failed: %s", exc)
            raise

    def parse(self, question: str, catalog: list[MetricInfo], today: date) -> ParsedQuestion:
        """
        #Feature: LLM routing
        #Scenario: Ask the model to route the question; fall back to rules if the call or its reply fails
        #Complexity: Time O(1) plus model latency

        Args:
            question: The user's question.
            catalog: Approved metrics.
            today: Workspace today.

        Returns:
            ParsedQuestion with source "llm", or the fallback's result.

        Raises:
            ValueError: When an argument is None.
        """
        try:
            if question is None or catalog is None or today is None:
                raise ValueError("[LLMQuestionParser.parse] 'question', 'catalog' and 'today' are required.")
            messages = [
                {"role": "system", "content": ROUTER_SYSTEM_PROMPT.format(today=today.isoformat(),
                                                                          catalog=render_catalog(catalog))},
                {"role": "user", "content": ROUTER_USER_PROMPT.format(question=question)},
            ]
            try:
                reply = RouterReply.model_validate(extract_json(self._complete(messages)))
            except Exception as model_exc:
                logger.warning("LLM routing failed, using fallback parser: %s", model_exc)
                return self._fallback.parse(question, catalog, today)
            return to_parsed(reply, catalog)
        except Exception as exc:
            logger.error("parse failed: %s", exc)
            raise
