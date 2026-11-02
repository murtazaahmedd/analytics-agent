import logging
import re
from datetime import date

from truemetric.constants import (
    AMBIGUOUS_TERMS,
    DIMENSION_SYNONYMS,
    FILTER_SKIP_DIMENSIONS,
    GRAIN_WORDS,
    METRIC_SYNONYMS,
    NUMBER_WORDS,
    OUT_OF_SCOPE_TERMS,
    RATE_WORDS,
    VALUE_ALIASES,
    WHY_MARKERS,
)
from truemetric.interfaces import IQuestionParser
from truemetric.schemas import Intent, MetricFilter, MetricInfo, MetricQuery, ParsedQuestion
from truemetric.utilities import parse_period

logger = logging.getLogger(__name__)


def normalize(question: str) -> str:
    """
    #Feature: Rule-based routing
    #Scenario: Lower-case, unhyphenate words ("session-to-cart", "90-day") and drop punctuation
    #Complexity: Time O(n)

    Args:
        question: Raw question.

    Returns:
        Normalised text padded with spaces.
    """
    try:
        text = question.lower()
        text = re.sub(r"(?<=[a-z0-9])-(?=[a-z])", " ", text)
        text = re.sub(r"[?!,;:()\"]", " ", text)
        return f" {re.sub(r'\s+', ' ', text).strip()} "
    except Exception as exc:
        logger.error("normalize failed: %s", exc)
        raise


def find_phrases(text: str, phrases: dict[str, str]) -> tuple[list[str], str]:
    """
    #Feature: Rule-based routing
    #Scenario: Longest-first, non-overlapping phrase matches; matched spans are blanked out
    #Complexity: Time O(p * n)

    Args:
        text: Normalised text.
        phrases: Phrase to target mapping.

    Returns:
        (targets in order of appearance, text with matches blanked).
    """
    try:
        hits: list[tuple[int, str]] = []
        for phrase in sorted(phrases, key=len, reverse=True):
            for match in re.finditer(rf"(?<![a-z0-9']){re.escape(phrase)}(?![a-z0-9])", text):
                hits.append((match.start(), phrases[phrase]))
                text = text[:match.start()] + " " * len(phrase) + text[match.end():]
        return [target for _, target in sorted(hits)], text
    except Exception as exc:
        logger.error("find_phrases failed: %s", exc)
        raise


def metric_phrases(catalog: list[MetricInfo]) -> dict[str, str]:
    """
    #Feature: Rule-based routing
    #Scenario: Synonyms plus each catalog metric's label and spaced name
    #Complexity: Time O(m)

    Args:
        catalog: Approved metrics.

    Returns:
        Phrase to metric name, restricted to metrics in the catalog.
    """
    try:
        names = {m.name for m in catalog}
        phrases = {p: n for p, n in METRIC_SYNONYMS.items() if n in names}
        for metric in catalog:
            phrases.setdefault(metric.label.lower(), metric.name)
            phrases.setdefault(metric.name.replace("_", " "), metric.name)
        return phrases
    except Exception as exc:
        logger.error("metric_phrases failed: %s", exc)
        raise


def order_and_limit(text: str, grouped: bool) -> tuple[str | None, int | None]:
    """
    #Feature: Rule-based routing
    #Scenario: "top 5", "top five", "which 5", "top <dimension>", "highest", "lowest" on grouped questions
    #Complexity: Time O(n)

    Args:
        text: Normalised text.
        grouped: Whether the question splits by a dimension.

    Returns:
        (order, limit).
    """
    try:
        numbers = "|".join([r"\d+", *NUMBER_WORDS])
        match = re.search(rf"\b(top|bottom|which)\s+({numbers})\b", text)
        if match:
            count = NUMBER_WORDS.get(match.group(2)) or int(match.group(2))
            return ("asc" if match.group(1) == "bottom" else "desc"), count
        if grouped and re.search(r"\b(top|highest|most|best|largest|biggest)\b", text):
            return "desc", 1
        if grouped and re.search(r"\b(lowest|least|worst|smallest)\b", text):
            return "asc", 1
        return None, None
    except Exception as exc:
        logger.error("order_and_limit failed: %s", exc)
        raise


def unknown_split(text: str, known: list[str]) -> str | None:
    """
    #Feature: Rule-based routing
    #Scenario: Detect "by <something>" where something is not a known dimension, grain or value.
    Blanked metric phrases leave runs of spaces, so "by <metric>" never matches the single-space pattern.
    #Complexity: Time O(k * n)

    Args:
        text: Normalised text with metric phrases blanked.
        known: Phrases that may legitimately follow "by".

    Returns:
        The unknown word, or None.
    """
    try:
        for match in re.finditer(r"\b(?:by|per|for each|split by|broken down by) ([a-z][a-z' ]*)", text):
            rest = match.group(1).strip()
            if rest and not any(rest.startswith(k) for k in known):
                return rest.split()[0]
        return None
    except Exception as exc:
        logger.error("unknown_split failed: %s", exc)
        raise


class RuleQuestionParser(IQuestionParser):
    """
    #Feature: Rule-based routing
    #Scenario: Deterministic parser for CI, evals and LLM fallback; refuses rather than guesses
    #Complexity: Time O(vocabulary * question length)
    """

    def __init__(self, dimension_values: dict[str, list[str]]) -> None:
        """
        #Feature: Rule-based routing
        #Scenario: Index known dimension values for filter matching
        #Complexity: Time O(values)

        Args:
            dimension_values: Short dimension name to its distinct values.
        """
        try:
            self._values: dict[str, str] = {}
            for dim, values in dimension_values.items():
                if dim in FILTER_SKIP_DIMENSIONS:
                    continue
                for value in values:
                    if len(value) >= 3:
                        self._values[value.lower()] = f"{dim}\t{value}"
            for alias, value in VALUE_ALIASES.items():
                if value.lower() in self._values:
                    self._values[alias] = self._values[value.lower()]
        except Exception as exc:
            logger.error("RuleQuestionParser init failed: %s", exc)
            raise

    def _filters(self, text: str) -> tuple[list[MetricFilter], str]:
        """
        #Feature: Rule-based routing
        #Scenario: Known dimension values in the question become equality filters
        #Complexity: Time O(values * n)

        Args:
            text: Normalised text.

        Returns:
            (filters, text with matched values blanked).
        """
        try:
            hits, text = find_phrases(text, self._values)
            grouped: dict[str, list[str]] = {}
            for hit in hits:
                dim, value = hit.split("\t")
                grouped.setdefault(dim, [])
                if value not in grouped[dim]:
                    grouped[dim].append(value)
            return [MetricFilter(dimension=d, values=v) for d, v in grouped.items()], text
        except Exception as exc:
            logger.error("_filters failed: %s", exc)
            raise

    def _metric_or_none(self, text: str, catalog: list[MetricInfo]) -> tuple[ParsedQuestion | None, str, str]:
        """
        #Feature: Rule-based routing
        #Scenario: Pick exactly one metric, or end early as unclear/out-of-scope
        #Complexity: Time O(phrases * n)

        Args:
            text: Normalised text.
            catalog: Approved metrics.

        Returns:
            (early result or None, metric name, text with metric phrases blanked).
        """
        try:
            metrics, rest = find_phrases(text, metric_phrases(catalog))
            unique = list(dict.fromkeys(metrics))
            if len(unique) > 1:
                return ParsedQuestion(intent=Intent.UNCLEAR, options=unique), "", rest
            if unique:
                return None, unique[0], rest
            ambiguous, _ = find_phrases(text, {t: t for t in AMBIGUOUS_TERMS})
            if ambiguous:
                return ParsedQuestion(intent=Intent.UNCLEAR, options=AMBIGUOUS_TERMS[ambiguous[0]]), "", rest
            return ParsedQuestion(intent=Intent.OUT_OF_SCOPE, gap="what was asked"), "", rest
        except Exception as exc:
            logger.error("_metric_or_none failed: %s", exc)
            raise

    def _query(self, metric: str, text: str, rest: str, today: date) -> ParsedQuestion:
        """
        #Feature: Rule-based routing
        #Scenario: Assemble the metric query from filters, splits, grain, period and ordering
        #Complexity: Time O(vocabulary * n)

        Args:
            metric: Chosen metric.
            text: Normalised text.
            rest: Text with metric phrases blanked.
            today: Workspace today.

        Returns:
            ParsedQuestion with intent WHAT or OUT_OF_SCOPE.
        """
        try:
            filters, rest = self._filters(rest)
            unknown = unknown_split(rest, [*DIMENSION_SYNONYMS, *GRAIN_WORDS, "the ", "month", "day", "week",
                                           "quarter", "year"])
            if unknown:
                return ParsedQuestion(intent=Intent.OUT_OF_SCOPE, gap=f"{metric} split by '{unknown}'")
            dims, _ = find_phrases(rest, DIMENSION_SYNONYMS)
            filtered = {f.dimension for f in filters}
            group_by = [d for d in dict.fromkeys(dims) if d not in filtered]
            grains, _ = find_phrases(text, GRAIN_WORDS)
            period = parse_period(text, today)
            order, limit = order_and_limit(text, bool(group_by))
            query = MetricQuery(metric=metric, group_by=group_by, filters=filters, grain=grains[0] if grains else None,
                                start=period[0] if period else None, end=period[1] if period else None,
                                order=order, limit=limit)
            return ParsedQuestion(intent=Intent.WHAT, query=query)
        except Exception as exc:
            logger.error("_query failed: %s", exc)
            raise

    def parse(self, question: str, catalog: list[MetricInfo], today: date) -> ParsedQuestion:
        """
        #Feature: Rule-based routing
        #Scenario: Out-of-scope terms, then metric, rate words, why markers, then the query
        #Complexity: Time O(vocabulary * question length)

        Args:
            question: The user's question.
            catalog: Approved metrics.
            today: Workspace today.

        Returns:
            ParsedQuestion with source "rules".

        Raises:
            ValueError: When an argument is None.
        """
        try:
            if question is None or catalog is None or today is None:
                raise ValueError("[RuleQuestionParser.parse] 'question', 'catalog' and 'today' are required.")
            text = normalize(question)
            out_of_scope, _ = find_phrases(text, {t: t for t in OUT_OF_SCOPE_TERMS})
            if out_of_scope:
                return ParsedQuestion(intent=Intent.OUT_OF_SCOPE, gap=f"'{out_of_scope[0]}'")
            early, metric, rest = self._metric_or_none(text, catalog)
            units = {m.name: m.unit for m in catalog}
            if metric and units.get(metric) != "percent" and any(w in text for w in RATE_WORDS):
                return ParsedQuestion(intent=Intent.OUT_OF_SCOPE, gap=f"a rate or share based on {metric}")
            if any(marker in text for marker in WHY_MARKERS):
                query = MetricQuery(metric=metric) if metric else None
                return ParsedQuestion(intent=Intent.WHY, query=query, options=early.options if early else [])
            return early or self._query(metric, text, rest, today)
        except Exception as exc:
            logger.error("parse failed: %s", exc)
            raise
