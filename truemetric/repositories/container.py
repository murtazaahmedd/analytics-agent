import logging
from pathlib import Path

from metricflow.engine.metricflow_engine import AbstractMetricFlowEngine

from truemetric.connectors import DuckDBConnector
from truemetric.interfaces import Completion, ITracer, IWarehouseConnector
from truemetric.repositories.jsonl_tracer import JsonlTracer
from truemetric.repositories.llm_gateway import litellm_completion
from truemetric.repositories.metricflow_engine import load_engine
from truemetric.repositories.project_files import load_checks_config, load_manifest
from truemetric.schemas import ChecksConfig, WorkspaceConfig
from truemetric.utilities import ManifestIndex

logger = logging.getLogger(__name__)


class RepositoryContainer:
    """
    #Feature: Composition root
    #Scenario: Lazily created data-access dependencies for one workspace (warehouse, files, engine, LLM, traces)
    #Complexity: Time O(1) per property after first access
    """

    def __init__(self, config: WorkspaceConfig) -> None:
        """
        #Feature: Composition root
        #Scenario: Hold the workspace config; nothing is opened until first use
        #Complexity: Time O(1)

        Args:
            config: Workspace settings.

        Raises:
            ValueError: When config is None.
        """
        try:
            if config is None:
                raise ValueError("[RepositoryContainer.__init__] 'config' is required.")
            self._config, self._project = config, Path(config.dbt_project_dir).resolve()
            self._connector: IWarehouseConnector | None = None
            self._manifest: ManifestIndex | None = None
            self._checks_config: ChecksConfig | None = None
            self._tracer: ITracer | None = None
            self._completion: Completion | None = None
        except Exception as exc:
            logger.error("RepositoryContainer init failed: %s", exc)
            raise

    @property
    def connector(self) -> IWarehouseConnector:
        """
        #Feature: Composition root
        #Scenario: Read-only warehouse connector
        #Complexity: Time O(1)
        """
        try:
            if self._connector is None:
                self._connector = DuckDBConnector(self._config.duckdb_path, self._config.mart_schema,
                                                  self._config.max_result_rows, self._config.workspace_id)
            return self._connector
        except Exception as exc:
            logger.error("connector failed: %s", exc, extra={"tenant_id": self._config.workspace_id})
            raise

    @property
    def engine(self) -> AbstractMetricFlowEngine:
        """
        #Feature: Composition root
        #Scenario: MetricFlow engine (cached per dbt project across workspaces)
        #Complexity: Time O(1) after first build
        """
        try:
            return load_engine(str(self._project), Path(self._config.duckdb_path).name)
        except Exception as exc:
            logger.error("engine failed: %s", exc, extra={"tenant_id": self._config.workspace_id})
            raise

    @property
    def manifest(self) -> ManifestIndex:
        """
        #Feature: Composition root
        #Scenario: Semantic manifest of the workspace's metric repo
        #Complexity: Time O(manifest size) once
        """
        try:
            if self._manifest is None:
                self._manifest = load_manifest(self._project)
            return self._manifest
        except Exception as exc:
            logger.error("manifest failed: %s", exc, extra={"tenant_id": self._config.workspace_id})
            raise

    @property
    def checks_config(self) -> ChecksConfig:
        """
        #Feature: Composition root
        #Scenario: Data health check configuration
        #Complexity: Time O(file size) once
        """
        try:
            if self._checks_config is None:
                self._checks_config = load_checks_config(self._project)
            return self._checks_config
        except Exception as exc:
            logger.error("checks_config failed: %s", exc, extra={"tenant_id": self._config.workspace_id})
            raise

    @property
    def tracer(self) -> ITracer:
        """
        #Feature: Composition root
        #Scenario: Trace store
        #Complexity: Time O(1)
        """
        try:
            if self._tracer is None:
                self._tracer = JsonlTracer(self._config.trace_dir)
            return self._tracer
        except Exception as exc:
            logger.error("tracer failed: %s", exc, extra={"tenant_id": self._config.workspace_id})
            raise

    @property
    def completion(self) -> Completion | None:
        """
        #Feature: Composition root
        #Scenario: LLM gateway, or None when the workspace uses the rule-based router
        #Complexity: Time O(1)
        """
        try:
            if self._completion is None and self._config.llm is not None:
                self._completion = litellm_completion(self._config.llm)
            return self._completion
        except Exception as exc:
            logger.error("completion failed: %s", exc, extra={"tenant_id": self._config.workspace_id})
            raise
