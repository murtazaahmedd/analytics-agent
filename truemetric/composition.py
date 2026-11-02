import logging
import os
from datetime import datetime

from truemetric.constants import (
    ENV_AS_OF,
    ENV_DBT_PROJECT_DIR,
    ENV_LLM_FALLBACKS,
    ENV_LLM_MODEL,
    ENV_LLM_REASONING_EFFORT,
    ENV_LLM_TIMEOUT,
    ENV_WAREHOUSE_PATH,
    ENV_WORKSPACE_ID,
    LLM_DEFAULT_TIMEOUT_SECONDS,
)
from truemetric.interfaces import IQuestionParser
from truemetric.repositories import RepositoryContainer
from truemetric.schemas import LLMSettings, WorkspaceConfig
from truemetric.services import ServiceContainer
from truemetric.utilities import UtilityContainer

logger = logging.getLogger(__name__)


def llm_settings_from_env() -> LLMSettings | None:
    """
    #Feature: Composition root
    #Scenario: Router model settings from TRUEMETRIC_LLM_* environment variables
    #Complexity: Time O(1)

    Returns:
        LLMSettings, or None when TRUEMETRIC_LLM_MODEL is unset (rule-based router).
    """
    try:
        model = os.environ.get(ENV_LLM_MODEL)
        if not model:
            return None
        return LLMSettings(model=model,
                           fallbacks=[m for m in os.environ.get(ENV_LLM_FALLBACKS, "").split(",") if m],
                           reasoning_effort=os.environ.get(ENV_LLM_REASONING_EFFORT) or None,
                           timeout_seconds=float(os.environ.get(ENV_LLM_TIMEOUT, LLM_DEFAULT_TIMEOUT_SECONDS)))
    except Exception as exc:
        logger.error("llm_settings_from_env failed: %s", exc)
        raise


def config_from_env() -> WorkspaceConfig:
    """
    #Feature: Composition root
    #Scenario: Workspace settings for standalone processes (MCP servers) from environment variables
    #Complexity: Time O(1)

    Returns:
        WorkspaceConfig.

    Raises:
        ValueError: When required variables are missing.
    """
    try:
        missing = [name for name in (ENV_WORKSPACE_ID, ENV_DBT_PROJECT_DIR, ENV_WAREHOUSE_PATH)
                   if not os.environ.get(name)]
        if missing:
            raise ValueError(f"[config_from_env] Missing environment variables: {', '.join(missing)}. "
                             "Fix: export them before starting the server.")
        as_of = os.environ.get(ENV_AS_OF)
        return WorkspaceConfig(workspace_id=os.environ[ENV_WORKSPACE_ID],
                               dbt_project_dir=os.environ[ENV_DBT_PROJECT_DIR],
                               duckdb_path=os.environ[ENV_WAREHOUSE_PATH],
                               as_of=datetime.fromisoformat(as_of) if as_of else None,
                               llm=llm_settings_from_env())
    except Exception as exc:
        logger.error("config_from_env failed: %s", exc)
        raise


def build_services(config: WorkspaceConfig, parser: IQuestionParser | None = None) -> ServiceContainer:
    """
    #Feature: Composition root
    #Scenario: Wire UtilityContainer and RepositoryContainer into a ServiceContainer for one workspace
    #Complexity: Time O(1); dependencies are created lazily on first use

    Args:
        config: Workspace settings.
        parser: Optional parser override for tests and evals.

    Returns:
        ServiceContainer exposing semantic, warehouse, checks, parser and agent.

    Raises:
        ValueError: When config is None.
    """
    try:
        if config is None:
            raise ValueError("[build_services] 'config' is required. Fix: pass a WorkspaceConfig.")
        return ServiceContainer(config, UtilityContainer(config), RepositoryContainer(config), parser)
    except Exception as exc:
        logger.error("build_services failed: %s", exc)
        raise
