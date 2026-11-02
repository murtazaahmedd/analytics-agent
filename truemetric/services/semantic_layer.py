import logging
from datetime import datetime, time

from metricflow.engine.metricflow_engine import AbstractMetricFlowEngine, MetricFlowQueryRequest

from truemetric.errors import Errors
from truemetric.interfaces import ISemanticLayer, IWarehouseConnector
from truemetric.schemas import MetricInfo, MetricQuery, MetricResult
from truemetric.constants import GRAINS, METRIC_TIME
from truemetric.utilities import ManifestIndex, quote_identifier, quote_literal, require, to_plain

logger = logging.getLogger(__name__)


def pick_dimension(candidates: list[str], preferred_entity: str | None) -> str | None:
    """
    #Feature: Semantic layer
    #Scenario: Choose among qualified dimensions sharing a short name (shortest join path first)
    #Complexity: Time O(c log c)

    Args:
        candidates: Qualified names ending in the requested short name.
        preferred_entity: The metric's own primary entity, preferred on ties.

    Returns:
        The chosen qualified name, or None when there are no candidates.
    """
    try:
        if not candidates:
            return None
        return min(candidates, key=lambda c: (c.count("__"), not c.startswith(f"{preferred_entity}__"), c))
    except Exception as exc:
        logger.error("pick_dimension failed: %s", exc)
        raise


def where_clause(dimension: str, values: list[str]) -> str:
    """
    #Feature: Semantic layer
    #Scenario: MetricFlow where filter for an IN list on a categorical dimension
    #Complexity: Time O(v)

    Args:
        dimension: Qualified dimension name.
        values: Allowed values.

    Returns:
        A Jinja-templated MetricFlow where constraint.
    """
    try:
        listed = ", ".join(quote_literal(v) for v in values)
        return f"{{{{ Dimension('{dimension}') }}}} in ({listed})"
    except Exception as exc:
        logger.error("where_clause failed for dimension=%s: %s", dimension, exc)
        raise


class MetricFlowSemanticLayer(ISemanticLayer):
    """
    #Feature: Semantic layer tools
    #Scenario: MetricFlow compiles metric queries; the read-only connector executes them
    #Complexity: Time O(query)
    """

    def __init__(self, engine: AbstractMetricFlowEngine, index: ManifestIndex,
                 connector: IWarehouseConnector, workspace_id: str) -> None:
        """
        #Feature: Semantic layer tools
        #Scenario: Build the metric catalog once per workspace
        #Complexity: Time O(metrics * dimensions)

        Args:
            engine: MetricFlow engine used only to compile SQL.
            index: Lookups over the semantic manifest.
            connector: Read-only warehouse connector.
            workspace_id: Tenant id for logs.
        """
        try:
            self._engine, self._index, self._connector, self._workspace_id = engine, index, connector, workspace_id
            self._catalog = {m.name: m for m in self._build_catalog()}
        except Exception as exc:
            logger.error("MetricFlowSemanticLayer init failed: %s", exc, extra={"tenant_id": workspace_id})
            raise

    def _build_catalog(self) -> list[MetricInfo]:
        """
        #Feature: Semantic layer tools
        #Scenario: Join MetricFlow's reachable dimensions with manifest labels, units and tables
        #Complexity: Time O(metrics * dimensions)

        Returns:
            One MetricInfo per metric.
        """
        try:
            catalog = []
            for metric in self._engine.list_metrics(include_dimensions=True):
                raw = self._index.metrics[metric.name]
                dims = sorted({d.dunder_name for d in metric.dimensions if d.type.value == "categorical"})
                tables = [self._index.model_table(m) for m in self._index.metric_models(metric.name)]
                catalog.append(MetricInfo(
                    name=metric.name, label=raw.get("label") or metric.name, description=raw.get("description") or "",
                    unit=(raw.get("config") or {}).get("meta", {}).get("unit", "number"),
                    dimensions=dims, tables=tables))
            return catalog
        except Exception as exc:
            logger.error("_build_catalog failed: %s", exc, extra={"tenant_id": self._workspace_id})
            raise

    def list_metrics(self) -> list[MetricInfo]:
        """
        #Feature: Semantic layer tools
        #Scenario: List approved metrics from the cached catalog
        #Complexity: Time O(m)

        Returns:
            All approved metrics.
        """
        try:
            return list(self._catalog.values())
        except Exception as exc:
            logger.error("list_metrics failed: %s", exc, extra={"tenant_id": self._workspace_id})
            raise

    def describe_metric(self, name: str) -> MetricInfo:
        """
        #Feature: Semantic layer tools
        #Scenario: Look up one metric's definition
        #Complexity: Time O(1)

        Args:
            name: Metric name.

        Returns:
            The metric.

        Raises:
            ValueError: When name is None.
            Errors.Misc.UnknownMetric: When the metric is not defined.
        """
        try:
            require("MetricFlowSemanticLayer.describe_metric", name=(name, str))
            if name not in self._catalog:
                raise Errors.Misc.UnknownMetric(
                    f"[MetricFlowSemanticLayer.describe_metric] Metric {name!r} is not defined in workspace "
                    f"{self._workspace_id}. Fix: pick one of list_metrics() or draft a new metric."
                )
            return self._catalog[name]
        except Exception as exc:
            logger.warning("describe_metric failed: %s", exc, extra={"tenant_id": self._workspace_id})
            raise

    def resolve_dimension(self, metric: str, name: str) -> str:
        """
        #Feature: Semantic layer tools
        #Scenario: Map a short dimension name (country) to a qualified one reachable from the metric
        #Complexity: Time O(dimensions)

        Args:
            metric: Metric name.
            name: Short or qualified dimension name.

        Returns:
            Qualified dimension name.

        Raises:
            Errors.Misc.InvalidDimension: When no reachable dimension matches.
        """
        try:
            info = self.describe_metric(metric)
            if name in info.dimensions:
                return name
            entity = self._index.primary_entity(self._index.metric_models(metric)[0])
            chosen = pick_dimension([d for d in info.dimensions if d.endswith(f"__{name}")], entity)
            if chosen is None:
                raise Errors.Misc.InvalidDimension(
                    f"[MetricFlowSemanticLayer.resolve_dimension] {metric!r} cannot be split or filtered by "
                    f"{name!r}. Available: {', '.join(info.dimensions)}. Fix: choose an available dimension."
                )
            return chosen
        except Exception as exc:
            logger.warning("resolve_dimension failed: %s", exc, extra={"tenant_id": self._workspace_id})
            raise

    def tables_for(self, query: MetricQuery) -> list[str]:
        """
        #Feature: Semantic layer tools
        #Scenario: Every mart a query reads, so the data guard can check them first
        #Complexity: Time O(dimensions * models)

        Args:
            query: Metric query.

        Returns:
            Unique table names, metric tables first.
        """
        try:
            tables = list(self.describe_metric(query.metric).tables)
            for name in query.group_by + [f.dimension for f in query.filters]:
                source = self._index.dimension_source(self.resolve_dimension(query.metric, name))
                if source:
                    tables.append(self._index.model_table(source[0]))
            return list(dict.fromkeys(tables))
        except Exception as exc:
            logger.warning("tables_for failed: %s", exc, extra={"tenant_id": self._workspace_id})
            raise

    def dimension_values(self, dimension: str) -> list[str]:
        """
        #Feature: Semantic layer tools
        #Scenario: Distinct values of a categorical dimension, for filter matching
        #Complexity: Time O(query)

        Args:
            dimension: Qualified dimension name, e.g. user__country.

        Returns:
            Sorted distinct non-null values.

        Raises:
            ValueError: When dimension is None.
            Errors.Misc.InvalidDimension: When the dimension is unknown.
        """
        try:
            require("MetricFlowSemanticLayer.dimension_values", dimension=(dimension, str))
            source = self._index.dimension_source(dimension)
            if source is None:
                raise Errors.Misc.InvalidDimension(
                    f"[MetricFlowSemanticLayer.dimension_values] Unknown categorical dimension {dimension!r}. "
                    "Fix: pass a qualified name such as user__country."
                )
            table = self._connector.qualify(self._index.model_table(source[0]))
            column = quote_identifier(source[1])
            _, rows = self._connector.execute(f"select distinct {column} from {table} where {column} is not null")
            return sorted(str(r[0]) for r in rows)
        except Exception as exc:
            logger.warning("dimension_values failed: %s", exc, extra={"tenant_id": self._workspace_id})
            raise

    def _request(self, query: MetricQuery) -> MetricFlowQueryRequest:
        """
        #Feature: Semantic layer tools
        #Scenario: Translate a MetricQuery into a MetricFlow request
        #Complexity: Time O(dimensions)

        Args:
            query: Metric query with resolved, qualified dimensions.

        Returns:
            MetricFlow request.
        """
        try:
            time_dim = [f"{METRIC_TIME}__{query.grain}"] if query.grain else []
            order = [f"-{query.metric}" if query.order == "desc" else query.metric] if query.order else time_dim
            return MetricFlowQueryRequest.create(
                metric_names=[query.metric], group_by_names=time_dim + query.group_by,
                time_constraint_start=datetime.combine(query.start, time(0)) if query.start else None,
                time_constraint_end=datetime.combine(query.end, time(0)) if query.end else None,
                where_constraints=[where_clause(f.dimension, f.values) for f in query.filters] or None,
                order_by_names=order + query.group_by, limit=query.limit)
        except Exception as exc:
            logger.error("_request failed: %s", exc, extra={"tenant_id": self._workspace_id})
            raise

    def _resolve(self, query: MetricQuery) -> MetricQuery:
        """
        #Feature: Semantic layer tools
        #Scenario: Qualify dimensions and enforce the metric's native grain
        #Complexity: Time O(dimensions)

        Args:
            query: Query as requested.

        Returns:
            Query with qualified dimensions and a grain set for month-only metrics.
        """
        try:
            native = self._index.metric_grain(query.metric)
            grain = query.grain
            if native != GRAINS[0] and (grain is None or GRAINS.index(grain) < GRAINS.index(native)):
                grain = native
            group_by = [self.resolve_dimension(query.metric, d) for d in query.group_by]
            filters = [f.model_copy(update={"dimension": self.resolve_dimension(query.metric, f.dimension)})
                       for f in query.filters]
            return query.model_copy(update={"group_by": group_by, "filters": filters, "grain": grain})
        except Exception as exc:
            logger.warning("_resolve failed: %s", exc, extra={"tenant_id": self._workspace_id})
            raise

    def query_metric(self, query: MetricQuery) -> MetricResult:
        """
        #Feature: Semantic layer tools
        #Scenario: Compile a metric query with MetricFlow and run it on the read-only connector
        #Complexity: Time O(query)

        Args:
            query: Structured metric query.

        Returns:
            Result rows and the SQL that produced them.

        Raises:
            ValueError: When query is None.
            Errors.Misc.UnknownMetric: When the metric is not defined.
            Errors.Misc.InvalidDimension: When a dimension, grain or filter cannot be compiled.
        """
        try:
            require("MetricFlowSemanticLayer.query_metric", query=(query, MetricQuery))
            resolved = self._resolve(query)
            try:
                sql = self._engine.explain(self._request(resolved)).sql_statement.sql
            except Exception as mf_exc:
                raise Errors.Misc.InvalidDimension(
                    f"[MetricFlowSemanticLayer.query_metric] MetricFlow could not compile the query: {mf_exc}. "
                    "Fix: change the grain, dimensions or filters."
                ) from mf_exc
            columns, rows = self._connector.execute(sql)
            records = [{c: to_plain(v) for c, v in zip(columns, row)} for row in rows]
            logger.info("query_metric ok metric=%s rows=%d", query.metric, len(records),
                        extra={"tenant_id": self._workspace_id})
            return MetricResult(query=resolved, columns=columns, rows=records, sql=sql)
        except Exception as exc:
            logger.warning("query_metric failed: %s", exc, extra={"tenant_id": self._workspace_id})
            raise
