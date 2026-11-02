import logging

from truemetric.agent import AgentGraph, AnswererNode, DataGuardNode, LLMQuestionParser, RouterNode, RuleQuestionParser
from truemetric.constants import CHECK_CACHE_TTL_SECONDS
from truemetric.interfaces import IDataChecks, IQuestionParser, ISemanticLayer, IWarehouseTools
from truemetric.repositories import RepositoryContainer
from truemetric.schemas import WorkspaceConfig
from truemetric.services.data_checks import WarehouseDataChecks
from truemetric.services.semantic_layer import MetricFlowSemanticLayer
from truemetric.services.warehouse_tools import WarehouseTools
from truemetric.utilities import UtilityContainer

logger = logging.getLogger(__name__)


class ServiceContainer:
    """
    #Feature: Composition root
    #Scenario: Lazily wired services and agent nodes for one workspace
    #Complexity: Time O(1) per property after first access
    """

    def __init__(self, config: WorkspaceConfig, utilities: UtilityContainer, repositories: RepositoryContainer,
                 parser: IQuestionParser | None = None) -> None:
        """
        #Feature: Composition root
        #Scenario: Receive the utility and repository containers by constructor injection
        #Complexity: Time O(1)

        Args:
            config: Workspace settings.
            utilities: Utility container (clock).
            repositories: Repository container (warehouse, files, engine, LLM, traces).
            parser: Optional parser override for tests and evals.

        Raises:
            ValueError: When a required container is None.
        """
        try:
            if config is None or utilities is None or repositories is None:
                raise ValueError("[ServiceContainer.__init__] 'config', 'utilities' and 'repositories' are required.")
            self.config, self._utilities, self._repositories = config, utilities, repositories
            self._workspace_id = config.workspace_id
            self._semantic: ISemanticLayer | None = None
            self._warehouse: IWarehouseTools | None = None
            self._checks: IDataChecks | None = None
            self._parser: IQuestionParser | None = parser
            self._agent: AgentGraph | None = None
        except Exception as exc:
            logger.error("ServiceContainer init failed: %s", exc)
            raise

    @property
    def semantic(self) -> ISemanticLayer:
        """
        #Feature: Composition root
        #Scenario: Semantic layer service
        #Complexity: Time O(catalog) once
        """
        try:
            if self._semantic is None:
                repos = self._repositories
                self._semantic = MetricFlowSemanticLayer(repos.engine, repos.manifest, repos.connector,
                                                         self._workspace_id)
            return self._semantic
        except Exception as exc:
            logger.error("semantic failed: %s", exc, extra={"tenant_id": self._workspace_id})
            raise

    @property
    def warehouse(self) -> IWarehouseTools:
        """
        #Feature: Composition root
        #Scenario: Read-only warehouse tools service
        #Complexity: Time O(1)
        """
        try:
            if self._warehouse is None:
                self._warehouse = WarehouseTools(self._repositories.connector, self._workspace_id)
            return self._warehouse
        except Exception as exc:
            logger.error("warehouse failed: %s", exc, extra={"tenant_id": self._workspace_id})
            raise

    @property
    def checks(self) -> IDataChecks:
        """
        #Feature: Composition root
        #Scenario: Data health checks service
        #Complexity: Time O(1)
        """
        try:
            if self._checks is None:
                self._checks = WarehouseDataChecks(self._repositories.connector, self._repositories.checks_config,
                                                   self._utilities.now, self._workspace_id, CHECK_CACHE_TTL_SECONDS)
            return self._checks
        except Exception as exc:
            logger.error("checks failed: %s", exc, extra={"tenant_id": self._workspace_id})
            raise

    def _dimension_values(self) -> dict[str, list[str]]:
        """
        #Feature: Composition root
        #Scenario: Distinct values per short dimension name, for the rule parser's filter matching
        #Complexity: Time O(dimensions * query)

        Returns:
            Short dimension name to values, read from the shortest-path qualified dimension.
        """
        try:
            shortest: dict[str, str] = {}
            for metric in self.semantic.list_metrics():
                for dim in metric.dimensions:
                    short = dim.split("__")[-1]
                    if short not in shortest or dim.count("__") < shortest[short].count("__"):
                        shortest[short] = dim
            return {short: self.semantic.dimension_values(dim) for short, dim in shortest.items()}
        except Exception as exc:
            logger.error("_dimension_values failed: %s", exc, extra={"tenant_id": self._workspace_id})
            raise

    @property
    def parser(self) -> IQuestionParser:
        """
        #Feature: Composition root
        #Scenario: LLM router with rule-based fallback when an LLM is configured, else rules only
        #Complexity: Time O(dimensions * query) once
        """
        try:
            if self._parser is None:
                rules = RuleQuestionParser(self._dimension_values())
                completion = self._repositories.completion
                self._parser = LLMQuestionParser(completion, rules) if completion else rules
            return self._parser
        except Exception as exc:
            logger.error("parser failed: %s", exc, extra={"tenant_id": self._workspace_id})
            raise

    @property
    def agent(self) -> AgentGraph:
        """
        #Feature: Composition root
        #Scenario: The agent decision flow with its nodes
        #Complexity: Time O(1) after dependencies are built
        """
        try:
            if self._agent is None:
                workspace_id = self._workspace_id
                router = RouterNode(self.parser, self.semantic, self._utilities.today, workspace_id)
                guard = DataGuardNode(self.semantic, self.checks, workspace_id)
                answerer = AnswererNode(self.semantic, workspace_id)
                self._agent = AgentGraph(router, guard, answerer, self.semantic, self._repositories.tracer,
                                         workspace_id)
            return self._agent
        except Exception as exc:
            logger.error("agent failed: %s", exc, extra={"tenant_id": self._workspace_id})
            raise
