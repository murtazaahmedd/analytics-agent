import logging
from collections.abc import Callable
from datetime import date

from truemetric.constants import VALUE_ALIASES
from truemetric.errors import Errors
from truemetric.interfaces import IQuestionParser, ISemanticLayer
from truemetric.schemas import Intent, MetricFilter, MetricQuery, ParsedQuestion
from truemetric.utilities import same_bucket

logger = logging.getLogger(__name__)


class RouterNode:
    """
    #Feature: Agent routing
    #Scenario: Classify the question and check its metric and dimensions exist before anything runs
    #Complexity: Time O(parse + dimensions)
    """

    def __init__(self, parser: IQuestionParser, semantic: ISemanticLayer, today: Callable[[], date],
                 workspace_id: str) -> None:
        """
        #Feature: Agent routing
        #Scenario: Inject the parser, the semantic layer and the workspace clock
        #Complexity: Time O(1)

        Args:
            parser: Question parser (LLM or rules).
            semantic: Semantic layer for catalog and dimension checks.
            today: Workspace "today".
            workspace_id: Tenant id for logs.
        """
        try:
            self._parser, self._semantic, self._today, self._workspace_id = parser, semantic, today, workspace_id
            self._known_values: dict[str, dict[str, str]] = {}
        except Exception as exc:
            logger.error("RouterNode init failed: %s", exc, extra={"tenant_id": workspace_id})
            raise

    def _canonical_value(self, metric: str, dimension: str, value: str) -> str | None:
        """
        #Feature: Agent routing
        #Scenario: Map a filter value to the exact spelling in the data ("brazil" -> "Brasil"), or None
        #Complexity: Time O(1) after the dimension's values are cached

        Args:
            metric: Metric name.
            dimension: Short or qualified dimension.
            value: Value as parsed.

        Returns:
            Canonical value, or None when the data has no such value.
        """
        try:
            qualified = self._semantic.resolve_dimension(metric, dimension)
            if qualified not in self._known_values:
                self._known_values[qualified] = {v.lower(): v for v in self._semantic.dimension_values(qualified)}
            known = self._known_values[qualified]
            lowered = value.strip().lower()
            return known.get(lowered) or known.get(VALUE_ALIASES.get(lowered, "").lower())
        except Exception as exc:
            logger.error("_canonical_value failed: %s", exc, extra={"tenant_id": self._workspace_id})
            raise

    def _normalize(self, query: MetricQuery) -> MetricQuery | str:
        """
        #Feature: Agent routing
        #Scenario: Canonicalise filter values, drop splits on single-value filters and single-bucket grains
        #Complexity: Time O(filters * values)

        Args:
            query: Query whose metric and dimensions are already validated.

        Returns:
            Normalised query, or a gap description when a filter value does not exist in the data.
        """
        try:
            filters = []
            for f in query.filters:
                values = [self._canonical_value(query.metric, f.dimension, v) for v in f.values]
                if None in values:
                    missing = f.values[values.index(None)]
                    return f"'{missing}' as a {f.dimension.split('__')[-1].replace('_', ' ')} value"
                filters.append(MetricFilter(dimension=f.dimension, values=list(dict.fromkeys(values))))
            single = {f.dimension for f in filters if len(f.values) == 1}
            group_by = [d for d in query.group_by if d not in single]
            grain = query.grain
            if grain and query.start and query.end and same_bucket(query.start, query.end, grain):
                grain = None
            return query.model_copy(update={"filters": filters, "group_by": group_by, "grain": grain})
        except Exception as exc:
            logger.error("_normalize failed: %s", exc, extra={"tenant_id": self._workspace_id})
            raise

    def _validate(self, parsed: ParsedQuestion) -> ParsedQuestion:
        """
        #Feature: Agent routing
        #Scenario: Gate 2 - does an approved metric define what was asked, with these dimensions?
        #Complexity: Time O(dimensions)

        Args:
            parsed: A WHAT question.

        Returns:
            The question unchanged, or OUT_OF_SCOPE naming the gap.
        """
        try:
            query = parsed.query
            try:
                label = self._semantic.describe_metric(query.metric).label
            except Errors.Misc.UnknownMetric:
                return ParsedQuestion(intent=Intent.OUT_OF_SCOPE, gap=f"'{query.metric}'", source=parsed.source)
            for dim in query.group_by + [f.dimension for f in query.filters]:
                try:
                    self._semantic.resolve_dimension(query.metric, dim)
                except Errors.Misc.InvalidDimension:
                    return ParsedQuestion(intent=Intent.OUT_OF_SCOPE, gap=f"{label} by {dim.replace('_', ' ')}",
                                          source=parsed.source)
            normalized = self._normalize(query)
            if isinstance(normalized, str):
                return ParsedQuestion(intent=Intent.OUT_OF_SCOPE, gap=normalized, source=parsed.source)
            return parsed.model_copy(update={"query": normalized})
        except Exception as exc:
            logger.error("_validate failed: %s", exc, extra={"tenant_id": self._workspace_id})
            raise

    def route(self, question: str) -> ParsedQuestion:
        """
        #Feature: Agent routing
        #Scenario: Parse then validate a question
        #Complexity: Time O(parse + dimensions)

        Args:
            question: The user's question.

        Returns:
            ParsedQuestion; WHAT only when the metric and dimensions are approved.
        """
        try:
            parsed = self._parser.parse(question, self._semantic.list_metrics(), self._today())
            if parsed.intent == Intent.WHAT and parsed.query is None:
                return ParsedQuestion(intent=Intent.OUT_OF_SCOPE, gap="what was asked", source=parsed.source)
            return self._validate(parsed) if parsed.intent == Intent.WHAT else parsed
        except Exception as exc:
            logger.error("route failed: %s", exc, extra={"tenant_id": self._workspace_id})
            raise
