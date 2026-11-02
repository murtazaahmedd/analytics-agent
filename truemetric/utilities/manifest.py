import logging
from typing import Any

from truemetric.constants.semantic import GRAINS

logger = logging.getLogger(__name__)


class ManifestIndex:
    """
    #Feature: Semantic layer
    #Scenario: Lookups over a MetricFlow semantic_manifest.json (pure, no I/O)
    #Complexity: Time O(models + metrics) to build, O(1) per lookup
    """

    def __init__(self, manifest: dict[str, Any]) -> None:
        """
        #Feature: Semantic layer
        #Scenario: Index metrics, measures and dimensions by name
        #Complexity: Time O(models + metrics)

        Args:
            manifest: Parsed semantic_manifest.json.

        Raises:
            ValueError: When manifest is None or missing required keys.
        """
        try:
            if manifest is None:
                raise ValueError("[ManifestIndex.__init__] 'manifest' is required. Fix: run dbt parse.")
            self.metrics = {m["name"]: m for m in manifest["metrics"]}
            self.models = {s["name"]: s for s in manifest["semantic_models"]}
            self._measure_model = {ms["name"]: s["name"] for s in manifest["semantic_models"] for ms in s["measures"]}
        except Exception as exc:
            logger.error("ManifestIndex init failed: %s", exc)
            raise

    def metric_models(self, metric: str) -> list[str]:
        """
        #Feature: Semantic layer
        #Scenario: Semantic models whose measures feed a metric, in first-use order
        #Complexity: Time O(measures)

        Args:
            metric: Metric name.

        Returns:
            Semantic model names.
        """
        try:
            measures = self.metrics[metric]["type_params"]["input_measures"]
            return list(dict.fromkeys(self._measure_model[m["name"]] for m in measures))
        except Exception as exc:
            logger.error("metric_models failed for metric=%s: %s", metric, exc)
            raise

    def model_table(self, model: str) -> str:
        """
        #Feature: Semantic layer
        #Scenario: The mart table behind a semantic model
        #Complexity: Time O(1)

        Args:
            model: Semantic model name.

        Returns:
            Unqualified table name.
        """
        try:
            return self.models[model]["node_relation"]["alias"]
        except Exception as exc:
            logger.error("model_table failed for model=%s: %s", model, exc)
            raise

    def metric_grain(self, metric: str) -> str:
        """
        #Feature: Semantic layer
        #Scenario: Coarsest native time granularity across the metric's models (e.g. month-only metrics)
        #Complexity: Time O(models)

        Args:
            metric: Metric name.

        Returns:
            One of day, week, month, quarter, year.
        """
        try:
            grains = []
            for name in self.metric_models(metric):
                model = self.models[name]
                agg_time = model["defaults"]["agg_time_dimension"]
                dim = next(d for d in model["dimensions"] if d["name"] == agg_time)
                grains.append(dim["type_params"]["time_granularity"])
            return max(grains, key=GRAINS.index)
        except Exception as exc:
            logger.error("metric_grain failed for metric=%s: %s", metric, exc)
            raise

    def primary_entity(self, model: str) -> str | None:
        """
        #Feature: Semantic layer
        #Scenario: Primary entity of a semantic model, used to break dimension-name ties
        #Complexity: Time O(entities)

        Args:
            model: Semantic model name.

        Returns:
            Entity name, or None.
        """
        try:
            return next((e["name"] for e in self.models[model]["entities"] if e["type"] == "primary"), None)
        except Exception as exc:
            logger.error("primary_entity failed for model=%s: %s", model, exc)
            raise

    def dimension_source(self, qualified: str) -> tuple[str, str] | None:
        """
        #Feature: Semantic layer
        #Scenario: Find the model and column behind a qualified dimension like order__user__country
        #Complexity: Time O(models)

        Args:
            qualified: Dimension name with entity path.

        Returns:
            Tuple of (semantic model name, column expression), or None for metric_time or unknown.
        """
        try:
            parts = qualified.split("__")
            if len(parts) < 2:
                return None
            entity, name = parts[-2], parts[-1]
            for model in self.models.values():
                owns = any(e["name"] == entity and e["type"] == "primary" for e in model["entities"])
                dim = next((d for d in model["dimensions"] if d["name"] == name), None)
                if owns and dim:
                    return model["name"], dim["expr"] or dim["name"]
            return None
        except Exception as exc:
            logger.error("dimension_source failed for dimension=%s: %s", qualified, exc)
            raise
