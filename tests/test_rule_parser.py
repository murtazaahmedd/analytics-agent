from datetime import date

from truemetric.agent.parsers import RuleQuestionParser
from truemetric.schemas import Intent, MetricInfo

TODAY = date(2026, 11, 1)


def test_simple_metric_and_period(catalog: list[MetricInfo], values: dict[str, list[str]]) -> None:
    """
    #Feature: Rule-based routing
    #Scenario: One metric and a period
    #Complexity: Time O(1)
    """
    parsed = RuleQuestionParser(values).parse("What was net revenue in March 2024?", catalog, TODAY)
    assert parsed.intent == Intent.WHAT
    assert parsed.query.metric == "net_revenue"
    assert (parsed.query.start, parsed.query.end) == (date(2024, 3, 1), date(2024, 3, 31))


def test_value_becomes_filter_not_split(catalog: list[MetricInfo], values: dict[str, list[str]]) -> None:
    """
    #Feature: Rule-based routing
    #Scenario: A known value filters; its dimension word does not also split
    #Complexity: Time O(1)
    """
    parsed = RuleQuestionParser(values).parse("Net revenue for the Brazil market in 2025", catalog, TODAY)
    assert [(f.dimension, f.values) for f in parsed.query.filters] == [("country", ["Brasil"])]
    assert parsed.query.group_by == []


def test_top_n_split(catalog: list[MetricInfo], values: dict[str, list[str]]) -> None:
    """
    #Feature: Rule-based routing
    #Scenario: "Top 3 countries by <metric>" splits, orders and limits
    #Complexity: Time O(1)
    """
    query = RuleQuestionParser(values).parse("Top 3 countries by gross revenue last year", catalog, TODAY).query
    assert (query.group_by, query.order, query.limit) == (["country"], "desc", 3)


def test_ambiguous_asks(catalog: list[MetricInfo], values: dict[str, list[str]]) -> None:
    """
    #Feature: Rule-based routing
    #Scenario: "sales" could mean several metrics
    #Complexity: Time O(1)
    """
    parsed = RuleQuestionParser(values).parse("How are sales doing?", catalog, TODAY)
    assert parsed.intent == Intent.UNCLEAR
    assert "net_revenue" in parsed.options


def test_out_of_scope_terms_win_over_metric_words(catalog: list[MetricInfo], values: dict[str, list[str]]) -> None:
    """
    #Feature: Rule-based routing
    #Scenario: "revenue per session" must not be answered as revenue or sessions
    #Complexity: Time O(1)
    """
    parsed = RuleQuestionParser(values).parse("Revenue per session last month", catalog, TODAY)
    assert parsed.intent == Intent.OUT_OF_SCOPE


def test_unknown_split_refuses(catalog: list[MetricInfo], values: dict[str, list[str]]) -> None:
    """
    #Feature: Rule-based routing
    #Scenario: Splitting by an unmodelled dimension refuses instead of dropping the split
    #Complexity: Time O(1)
    """
    parsed = RuleQuestionParser(values).parse("Gross revenue by city last month", catalog, TODAY)
    assert parsed.intent == Intent.OUT_OF_SCOPE
    assert "city" in parsed.gap


def test_two_metrics_ask(catalog: list[MetricInfo], values: dict[str, list[str]]) -> None:
    """
    #Feature: Rule-based routing
    #Scenario: Two metrics in one question - ask which one
    #Complexity: Time O(1)
    """
    parsed = RuleQuestionParser(values).parse("Gross revenue and sessions last week", catalog, TODAY)
    assert parsed.intent == Intent.UNCLEAR


def test_why_question(catalog: list[MetricInfo], values: dict[str, list[str]]) -> None:
    """
    #Feature: Rule-based routing
    #Scenario: Why-questions are routed separately and keep the metric
    #Complexity: Time O(1)
    """
    parsed = RuleQuestionParser(values).parse("Why did sessions drop last week?", catalog, TODAY)
    assert parsed.intent == Intent.WHY
    assert parsed.query.metric == "sessions"


def test_status_values_are_not_filters(catalog: list[MetricInfo], values: dict[str, list[str]]) -> None:
    """
    #Feature: Rule-based routing
    #Scenario: Common words that are also status values do not become filters
    #Complexity: Time O(1)
    """
    query = RuleQuestionParser(values).parse("Units sold, complete picture, in 2025", catalog, TODAY).query
    assert query.filters == []


def test_comparison_is_not_answered_with_one_number(catalog: list[MetricInfo], values: dict[str, list[str]]) -> None:
    """
    #Feature: Rule-based routing
    #Scenario: "Did X change week over week?" must not return a single all-time value
    #Complexity: Time O(1)
    """
    parsed = RuleQuestionParser(values).parse("Did sessions change week over week?", catalog, TODAY)
    assert parsed.intent == Intent.WHY


def test_rate_question_on_count_metric_refuses(catalog: list[MetricInfo], values: dict[str, list[str]]) -> None:
    """
    #Feature: Rule-based routing
    #Scenario: "What share of ..." must never be answered with a count
    #Complexity: Time O(1)
    """
    parsed = RuleQuestionParser(values).parse("What share of sessions came from Chrome last month?", catalog, TODAY)
    assert parsed.intent == Intent.OUT_OF_SCOPE


def test_number_words_and_which_n(catalog: list[MetricInfo], values: dict[str, list[str]]) -> None:
    """
    #Feature: Rule-based routing
    #Scenario: "top five" and "which 3" keep their limits
    #Complexity: Time O(1)
    """
    parser = RuleQuestionParser(values)
    assert parser.parse("Gross revenue by country in 2025, top five", catalog, TODAY).query.limit == 5
    assert parser.parse("Which 3 countries had the most gross revenue in 2025?", catalog, TODAY).query.limit == 3


def test_demonym_filters(catalog: list[MetricInfo], values: dict[str, list[str]]) -> None:
    """
    #Feature: Rule-based routing
    #Scenario: "Brazilian customers" filters to Brasil
    #Complexity: Time O(1)
    """
    query = RuleQuestionParser(values).parse("Net revenue from Brazilian customers in 2025", catalog, TODAY).query
    assert query.filters[0].values == ["Brasil"]
