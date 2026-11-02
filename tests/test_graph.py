from datetime import date, datetime
from typing import Any

from truemetric.agent import AgentGraph, AnswererNode, DataGuardNode, RouterNode
from truemetric.errors import Errors
from truemetric.interfaces import IDataChecks, IQuestionParser, ISemanticLayer, ITracer
from truemetric.schemas import (
    CheckResult,
    CheckRun,
    Intent,
    MetricFilter,
    MetricInfo,
    MetricQuery,
    MetricResult,
    Outcome,
    ParsedQuestion,
)


class FakeSemantic(ISemanticLayer):
    """
    #Feature: Test doubles
    #Scenario: Semantic layer with a fixed catalog; counts queries so tests can prove none ran
    #Complexity: Time O(1)
    """

    def __init__(self, catalog: list[MetricInfo], values: dict[str, list[str]], fail_query: bool) -> None:
        """
        #Feature: Test doubles
        #Scenario: Configure catalog, known values and failure mode
        #Complexity: Time O(m)
        """
        self.catalog, self.values = {m.name: m for m in catalog}, values
        self.queries, self.fail_query = 0, fail_query

    def list_metrics(self) -> list[MetricInfo]:
        """
        #Feature: Test doubles
        #Scenario: Return the fixed catalog
        #Complexity: Time O(m)
        """
        return list(self.catalog.values())

    def describe_metric(self, name: str) -> MetricInfo:
        """
        #Feature: Test doubles
        #Scenario: Look up a metric or raise UnknownMetric
        #Complexity: Time O(1)
        """
        if name not in self.catalog:
            raise Errors.Misc.UnknownMetric(name)
        return self.catalog[name]

    def resolve_dimension(self, metric: str, name: str) -> str:
        """
        #Feature: Test doubles
        #Scenario: Suffix match on qualified dimensions
        #Complexity: Time O(d)
        """
        match = [d for d in self.describe_metric(metric).dimensions if d.endswith(f"__{name}")]
        if not match:
            raise Errors.Misc.InvalidDimension(name)
        return match[0]

    def tables_for(self, query: MetricQuery) -> list[str]:
        """
        #Feature: Test doubles
        #Scenario: Tables behind the metric
        #Complexity: Time O(1)
        """
        return self.describe_metric(query.metric).tables

    def dimension_values(self, dimension: str) -> list[str]:
        """
        #Feature: Test doubles
        #Scenario: Known values by short dimension name
        #Complexity: Time O(1)
        """
        return self.values.get(dimension.split("__")[-1], [])

    def query_metric(self, query: MetricQuery) -> MetricResult:
        """
        #Feature: Test doubles
        #Scenario: Fixed result, or a failure
        #Complexity: Time O(1)
        """
        self.queries += 1
        if self.fail_query:
            raise RuntimeError("warehouse down")
        return MetricResult(query=query, columns=[query.metric], rows=[{query.metric: 1234.5}], sql="select 1")


class FakeChecks(IDataChecks):
    """
    #Feature: Test doubles
    #Scenario: Checks that pass or fail on demand
    #Complexity: Time O(1)
    """

    def __init__(self, passed: bool) -> None:
        """
        #Feature: Test doubles
        #Scenario: Fix the check outcome
        #Complexity: Time O(1)
        """
        self.passed = passed

    def run_checks(self, tables: list[str]) -> CheckRun:
        """
        #Feature: Test doubles
        #Scenario: One freshness result per table
        #Complexity: Time O(t)
        """
        return CheckRun(ran_at=datetime(2026, 11, 1), results=[
            CheckResult(table=t, check="freshness", passed=self.passed, detail="x") for t in tables])

    def get_last_run(self) -> CheckRun | None:
        """
        #Feature: Test doubles
        #Scenario: No history
        #Complexity: Time O(1)
        """
        return None


class FixedParser(IQuestionParser):
    """
    #Feature: Test doubles
    #Scenario: Parser returning a preset result
    #Complexity: Time O(1)
    """

    def __init__(self, parsed: ParsedQuestion) -> None:
        """
        #Feature: Test doubles
        #Scenario: Store the preset result
        #Complexity: Time O(1)
        """
        self.parsed = parsed

    def parse(self, question: str, catalog: list[MetricInfo], today: date) -> ParsedQuestion:
        """
        #Feature: Test doubles
        #Scenario: Ignore input, return the preset
        #Complexity: Time O(1)
        """
        return self.parsed


class NullTracer(ITracer):
    """
    #Feature: Test doubles
    #Scenario: Tracer that records event names
    #Complexity: Time O(1)
    """

    def __init__(self) -> None:
        """
        #Feature: Test doubles
        #Scenario: Start with no events
        #Complexity: Time O(1)
        """
        self.events: list[str] = []

    def start(self, workspace_id: str, question: str) -> str:
        """
        #Feature: Test doubles
        #Scenario: Constant trace id
        #Complexity: Time O(1)
        """
        return "trace"

    def event(self, trace_id: str, name: str, payload: dict[str, Any]) -> None:
        """
        #Feature: Test doubles
        #Scenario: Record the event name
        #Complexity: Time O(1)
        """
        self.events.append(name)


def graph(catalog: list[MetricInfo], parsed: ParsedQuestion, checks_pass: bool = True, fail_query: bool = False,
          values: dict[str, list[str]] | None = None) -> tuple[AgentGraph, FakeSemantic, NullTracer]:
    """
    #Feature: Test fixtures
    #Scenario: Agent wired with fakes
    #Complexity: Time O(1)
    """
    semantic, tracer = FakeSemantic(catalog, values or {}, fail_query), NullTracer()
    router = RouterNode(FixedParser(parsed), semantic, lambda: date(2026, 11, 1), "t")
    agent = AgentGraph(router, DataGuardNode(semantic, FakeChecks(checks_pass), "t"), AnswererNode(semantic, "t"),
                       semantic, tracer, "t")
    return agent, semantic, tracer


def what(metric: str, **kwargs: Any) -> ParsedQuestion:
    """
    #Feature: Test fixtures
    #Scenario: Shorthand for a WHAT question
    #Complexity: Time O(1)
    """
    return ParsedQuestion(intent=Intent.WHAT, query=MetricQuery(metric=metric, **kwargs))


def test_answers_through_semantic_layer(catalog: list[MetricInfo]) -> None:
    """
    #Feature: Agent decision flow
    #Scenario: Healthy data and an approved metric - answer with the number and definition
    #Complexity: Time O(1)
    """
    agent, _, _ = graph(catalog, what("net_revenue"))
    answer = agent.ask("net revenue?")
    assert answer.outcome == Outcome.ANSWERED and "$1,234.50" in answer.text and answer.definition


def test_failed_checks_block_before_query(catalog: list[MetricInfo]) -> None:
    """
    #Feature: Agent decision flow
    #Scenario: Gate 1 fails - no query runs, no number returned
    #Complexity: Time O(1)
    """
    agent, semantic, _ = graph(catalog, what("net_revenue"), checks_pass=False)
    answer = agent.ask("net revenue?")
    assert answer.outcome == Outcome.BLOCKED and semantic.queries == 0 and not answer.rows


def test_unknown_metric_is_refused_and_logged(catalog: list[MetricInfo]) -> None:
    """
    #Feature: Agent decision flow
    #Scenario: Gate 2 fails - refuse and record a metric gap
    #Complexity: Time O(1)
    """
    agent, semantic, tracer = graph(catalog, what("customer_ltv"))
    answer = agent.ask("ltv?")
    assert answer.outcome == Outcome.REFUSED and semantic.queries == 0 and "metric_gap" in tracer.events


def test_unreachable_dimension_is_refused(catalog: list[MetricInfo]) -> None:
    """
    #Feature: Agent decision flow
    #Scenario: Sessions cannot be split by product category
    #Complexity: Time O(1)
    """
    agent, _, _ = graph(catalog, what("sessions", group_by=["category"]))
    assert agent.ask("sessions by category").outcome == Outcome.REFUSED


def test_errors_fail_closed(catalog: list[MetricInfo]) -> None:
    """
    #Feature: Agent decision flow
    #Scenario: A failure mid-answer returns no number
    #Complexity: Time O(1)
    """
    agent, _, _ = graph(catalog, what("net_revenue"), fail_query=True)
    answer = agent.ask("net revenue?")
    assert answer.outcome == Outcome.ERROR and not answer.rows and "trace" in answer.text


def test_unknown_filter_value_is_refused(catalog: list[MetricInfo]) -> None:
    """
    #Feature: Agent routing
    #Scenario: An LLM filters on a value the data does not have - never answer "no data"
    #Complexity: Time O(1)
    """
    parsed = what("net_revenue", filters=[MetricFilter(dimension="country", values=["Atlantis"])])
    agent, semantic, _ = graph(catalog, parsed, values={"country": ["Brasil", "China"]})
    assert agent.ask("net revenue in Atlantis").outcome == Outcome.REFUSED and semantic.queries == 0


def test_filter_value_alias_and_normalisation(catalog: list[MetricInfo]) -> None:
    """
    #Feature: Agent routing
    #Scenario: "Brazil" maps to "Brasil"; a split on the filtered dimension and a single-bucket grain are dropped
    #Complexity: Time O(1)
    """
    parsed = what("net_revenue", group_by=["country"], grain="month", start=date(2025, 3, 1), end=date(2025, 3, 31),
                  filters=[MetricFilter(dimension="country", values=["Brazil"])])
    agent, _, _ = graph(catalog, parsed, values={"country": ["Brasil", "China"]})
    query = agent.ask("net revenue in brazil").query
    assert query.filters[0].values == ["Brasil"] and query.group_by == [] and query.grain is None
