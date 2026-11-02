import json
from datetime import date

from truemetric.agent.parsers import LLMQuestionParser, RuleQuestionParser
from truemetric.schemas import Intent, MetricInfo

TODAY = date(2026, 11, 1)


def test_valid_reply(catalog: list[MetricInfo], values: dict[str, list[str]]) -> None:
    """
    #Feature: LLM routing
    #Scenario: A valid model reply becomes a WHAT query
    #Complexity: Time O(1)
    """
    reply = {"intent": "what", "metric": "net_revenue", "group_by": ["country"], "start": "2024-03-01",
             "end": "2024-03-31", "order": "desc", "limit": 5}
    parser = LLMQuestionParser(lambda messages: "```json\n" + json.dumps(reply) + "\n```", RuleQuestionParser(values))
    parsed = parser.parse("net revenue by country", catalog, TODAY)
    assert parsed.intent == Intent.WHAT
    assert parsed.query.group_by == ["country"]
    assert parsed.query.limit == 5


def test_invented_metric_is_refused(catalog: list[MetricInfo], values: dict[str, list[str]]) -> None:
    """
    #Feature: LLM routing
    #Scenario: The model names a metric outside the catalog - never answered
    #Complexity: Time O(1)
    """
    reply = {"intent": "what", "metric": "customer_lifetime_value"}
    parser = LLMQuestionParser(lambda messages: json.dumps(reply), RuleQuestionParser(values))
    assert parser.parse("CLV?", catalog, TODAY).intent == Intent.OUT_OF_SCOPE


def test_model_failure_falls_back_to_rules(catalog: list[MetricInfo], values: dict[str, list[str]]) -> None:
    """
    #Feature: LLM routing
    #Scenario: Provider outage - the deterministic parser answers instead
    #Complexity: Time O(1)
    """
    def broken(messages: list[dict[str, str]]) -> str:
        """
        #Feature: Test doubles
        #Scenario: Provider outage
        #Complexity: Time O(1)
        """
        raise TimeoutError("provider down")

    parsed = LLMQuestionParser(broken, RuleQuestionParser(values)).parse("Net revenue in 2025", catalog, TODAY)
    assert parsed.query.metric == "net_revenue"


def test_prompt_contains_catalog_and_today(catalog: list[MetricInfo], values: dict[str, list[str]]) -> None:
    """
    #Feature: LLM routing
    #Scenario: The prompt lists approved metrics and today's date
    #Complexity: Time O(1)
    """
    seen: list[list[dict[str, str]]] = []

    def record(messages: list[dict[str, str]]) -> str:
        """
        #Feature: Test doubles
        #Scenario: Capture the prompt and return an unclear reply
        #Complexity: Time O(1)
        """
        seen.append(messages)
        return json.dumps({"intent": "unclear", "options": ["gross_revenue", "made_up"]})

    parsed = LLMQuestionParser(record, RuleQuestionParser(values)).parse("sales?", catalog, TODAY)
    assert "2026-11-01" in seen[0][0]["content"] and "gross_revenue" in seen[0][0]["content"]
    assert parsed.options == ["gross_revenue"]


def test_null_lists_are_accepted(catalog: list[MetricInfo], values: dict[str, list[str]]) -> None:
    """
    #Feature: LLM routing
    #Scenario: Models send null for empty lists; that must not force a fallback
    #Complexity: Time O(1)
    """
    reply = {"intent": "what", "metric": "net_revenue", "group_by": None, "filters": None, "options": None}
    parser = LLMQuestionParser(lambda messages: json.dumps(reply), RuleQuestionParser(values))
    assert parser.parse("net revenue", catalog, TODAY).source == "llm"
