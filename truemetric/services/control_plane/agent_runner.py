import logging
import threading
from collections.abc import Callable
from functools import lru_cache

from truemetric.agent import AgentGraph
from truemetric.interfaces import IAgentRunner
from truemetric.schemas import AgentAnswer, WorkspaceConfig

logger = logging.getLogger(__name__)


class CachedAgentRunner(IAgentRunner):
    """
    #Feature: Ask in plain English
    #Scenario: Keep the most recently used workspaces' agents loaded; run one question at a time
    #Complexity: Time O(agent) per question; O(engine startup) on a cache miss

    The agent and its caches were built for one caller at a time, so runs are serialised by a lock.
    That caps throughput per API process; Phase 3 moves agent runs to queue workers.
    """

    def __init__(self, build: Callable[[WorkspaceConfig], AgentGraph], maxsize: int) -> None:
        """
        #Feature: Ask in plain English
        #Scenario: Inject the agent builder from the composition root
        #Complexity: Time O(1)

        Args:
            build: Builds the agent for one workspace.
            maxsize: Workspaces kept loaded.

        Raises:
            ValueError: When build is None.
        """
        try:
            if build is None:
                raise ValueError("[CachedAgentRunner.__init__] 'build' is required.")
            self._build, self._lock = build, threading.Lock()
            self._agent_for_key = lru_cache(maxsize=maxsize)(self._build_from_key)
        except Exception as exc:
            logger.error("CachedAgentRunner init failed: %s", exc)
            raise

    def _build_from_key(self, key: str) -> AgentGraph:
        """
        #Feature: Ask in plain English
        #Scenario: Cache miss - build the agent from its serialised config
        #Complexity: Time O(engine startup)

        Args:
            key: WorkspaceConfig as JSON (hashable cache key; a changed setting is a new key).

        Returns:
            The workspace's agent.
        """
        try:
            config = WorkspaceConfig.model_validate_json(key)
            logger.info("loading agent", extra={"tenant_id": config.workspace_id})
            return self._build(config)
        except Exception as exc:
            logger.error("_build_from_key failed: %s", exc)
            raise

    def run(self, config: WorkspaceConfig, question: str) -> AgentAnswer:
        """
        #Feature: Ask in plain English
        #Scenario: Answer with the cached agent
        #Complexity: Time O(agent)
        """
        if config is None or question is None:
            raise ValueError("[CachedAgentRunner.run] 'config' and 'question' are required.")
        try:
            with self._lock:
                return self._agent_for_key(config.model_dump_json()).ask(question)
        except Exception as exc:
            logger.error("run failed: %s", exc, extra={"tenant_id": config.workspace_id})
            raise
