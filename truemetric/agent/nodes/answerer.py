import logging

from truemetric.interfaces import ISemanticLayer
from truemetric.schemas import MetricInfo, MetricQuery, MetricResult
from truemetric.utilities import format_value, period_label, render_table

logger = logging.getLogger(__name__)


def answer_text(result: MetricResult, info: MetricInfo) -> str:
    """
    #Feature: Answering
    #Scenario: Deterministic reply: the number(s), the period, and the metric definition
    #Complexity: Time O(rows)

    Args:
        result: Semantic layer result.
        info: Metric definition.

    Returns:
        Reply text. Numbers come only from result rows.
    """
    try:
        query = result.query
        period = period_label(query.start, query.end)
        definition = f"\n\nDefinition ({info.name}): {info.description}"
        if not result.rows:
            return f"No data matched for {info.label}, {period}.{definition}"
        if len(result.rows) == 1 and not query.group_by and not query.grain:
            return f"{info.label}, {period}: {format_value(result.rows[0][info.name], info.unit)}.{definition}"
        splits = [d.split("__")[-1].replace("_", " ") for d in query.group_by]
        title = f"{info.label} by {', '.join(splits)}" if splits else info.label
        if query.limit:
            title += f" ({'top' if query.order == 'desc' else 'bottom'} {query.limit})"
        table = render_table(result.columns, result.rows, info.name, info.unit)
        return f"{title}, {period}:\n\n{table}{definition}"
    except Exception as exc:
        logger.error("answer_text failed: %s", exc)
        raise


class AnswererNode:
    """
    #Feature: Answering
    #Scenario: Query the semantic layer and write the reply
    #Complexity: Time O(query)
    """

    def __init__(self, semantic: ISemanticLayer, workspace_id: str) -> None:
        """
        #Feature: Answering
        #Scenario: Inject the semantic layer
        #Complexity: Time O(1)

        Args:
            semantic: Semantic layer.
            workspace_id: Tenant id for logs.
        """
        try:
            self._semantic, self._workspace_id = semantic, workspace_id
        except Exception as exc:
            logger.error("AnswererNode init failed: %s", exc, extra={"tenant_id": workspace_id})
            raise

    def answer(self, query: MetricQuery) -> tuple[MetricResult, MetricInfo, str]:
        """
        #Feature: Answering
        #Scenario: Run the metric query and format it
        #Complexity: Time O(query)

        Args:
            query: Validated MetricQuery that passed the data guard.

        Returns:
            (result, metric definition, reply text).
        """
        try:
            result = self._semantic.query_metric(query)
            info = self._semantic.describe_metric(query.metric)
            return result, info, answer_text(result, info)
        except Exception as exc:
            logger.error("answer failed: %s", exc, extra={"tenant_id": self._workspace_id})
            raise
