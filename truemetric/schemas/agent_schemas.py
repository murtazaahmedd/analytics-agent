from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from truemetric.schemas.check_schemas import CheckResult
from truemetric.schemas.semantic_schemas import MetricQuery


class Intent(str, Enum):
    """
    #Feature: Agent routing
    #Scenario: What kind of question was asked
    #Complexity: Time O(1)
    """

    WHAT = "what"
    WHY = "why"
    UNCLEAR = "unclear"
    OUT_OF_SCOPE = "out_of_scope"


class Outcome(str, Enum):
    """
    #Feature: Agent routing
    #Scenario: The four end states of a question, plus not-yet-supported and fail-closed error
    #Complexity: Time O(1)
    """

    ANSWERED = "answered"
    BLOCKED = "blocked"
    REFUSED = "refused"
    CLARIFY = "clarify"
    UNSUPPORTED = "unsupported"
    ERROR = "error"


class ParsedQuestion(BaseModel):
    """
    #Feature: Agent routing
    #Scenario: A question parsed into intent and a candidate metric query
    #Complexity: Time O(1)

    gap describes the missing metric when intent is OUT_OF_SCOPE.
    options lists candidate metrics when intent is UNCLEAR.
    source is "llm" or "rules" (rules also covers LLM fallback).
    """

    intent: Intent
    query: MetricQuery | None = None
    gap: str | None = None
    options: list[str] = Field(default_factory=list)
    source: str = "rules"


class AskRequest(BaseModel):
    """
    #Feature: Ask in plain English
    #Scenario: A user question for one workspace
    #Complexity: Time O(1)
    """

    question: str = Field(min_length=1, max_length=1000)


class AgentAnswer(BaseModel):
    """
    #Feature: Ask in plain English
    #Scenario: The agent's reply, with everything needed to verify it
    #Complexity: Time O(1)
    """

    outcome: Outcome
    text: str
    trace_id: str
    metric: str | None = None
    definition: str | None = None
    query: MetricQuery | None = None
    sql: str | None = None
    columns: list[str] = Field(default_factory=list)
    rows: list[dict[str, Any]] = Field(default_factory=list)
    failed_checks: list[CheckResult] = Field(default_factory=list)
    options: list[str] = Field(default_factory=list)
    routed_by: str | None = None
