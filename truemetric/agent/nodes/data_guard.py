import logging

from truemetric.interfaces import IDataChecks, ISemanticLayer
from truemetric.schemas import CheckRun, MetricQuery

logger = logging.getLogger(__name__)


class DataGuardNode:
    """
    #Feature: Data guard
    #Scenario: Gate 1 - are the tables behind this answer fresh and valid? Fails closed.
    #Complexity: Time O(tables * checks)
    """

    def __init__(self, semantic: ISemanticLayer, checks: IDataChecks, workspace_id: str) -> None:
        """
        #Feature: Data guard
        #Scenario: Inject the semantic layer (to find tables) and the checks
        #Complexity: Time O(1)

        Args:
            semantic: Semantic layer.
            checks: Data checks.
            workspace_id: Tenant id for logs.
        """
        try:
            self._semantic, self._checks, self._workspace_id = semantic, checks, workspace_id
        except Exception as exc:
            logger.error("DataGuardNode init failed: %s", exc, extra={"tenant_id": workspace_id})
            raise

    def check(self, query: MetricQuery) -> CheckRun:
        """
        #Feature: Data guard
        #Scenario: Run checks on every mart the query reads
        #Complexity: Time O(tables * checks)

        Args:
            query: Validated metric query.

        Returns:
            CheckRun; the caller must not answer unless it passed.
        """
        try:
            return self._checks.run_checks(self._semantic.tables_for(query))
        except Exception as exc:
            logger.error("check failed: %s", exc, extra={"tenant_id": self._workspace_id})
            raise
