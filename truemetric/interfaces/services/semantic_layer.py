from abc import ABC, abstractmethod

from truemetric.schemas import MetricInfo, MetricQuery, MetricResult


class ISemanticLayer(ABC):
    """
    #Feature: Semantic layer tools
    #Scenario: The only path to a number shown to a user
    #Complexity: Time O(1) per call, plus query cost
    """

    @abstractmethod
    def list_metrics(self) -> list[MetricInfo]:
        """
        #Feature: Semantic layer tools
        #Scenario: List approved metrics with dimensions and backing tables
        #Complexity: Time O(m)

        Returns:
            All approved metrics.
        """

    @abstractmethod
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
            Errors.Misc.UnknownMetric: When the metric is not defined.
        """

    @abstractmethod
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

    @abstractmethod
    def tables_for(self, query: MetricQuery) -> list[str]:
        """
        #Feature: Semantic layer tools
        #Scenario: Every mart a query reads, so the data guard can check them first
        #Complexity: Time O(dimensions * models)

        Args:
            query: Metric query.

        Returns:
            Unique table names.
        """

    @abstractmethod
    def dimension_values(self, dimension: str) -> list[str]:
        """
        #Feature: Semantic layer tools
        #Scenario: Distinct values of a categorical dimension, for filter matching
        #Complexity: Time O(query)

        Args:
            dimension: Qualified dimension name, e.g. user__country.

        Returns:
            Sorted distinct non-null values.
        """

    @abstractmethod
    def query_metric(self, query: MetricQuery) -> MetricResult:
        """
        #Feature: Semantic layer tools
        #Scenario: Compile a metric query with MetricFlow and run it read-only
        #Complexity: Time O(query)

        Args:
            query: Structured metric query.

        Returns:
            Result rows and the SQL that produced them.

        Raises:
            Errors.Misc.UnknownMetric: When the metric is not defined.
            Errors.Misc.InvalidDimension: When a dimension is not reachable from the metric.
        """
