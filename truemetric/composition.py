import logging
import os
from datetime import datetime
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from truemetric.agent import AgentGraph
from truemetric.constants import (
    ENV_AS_OF,
    ENV_DATABASE_URL,
    ENV_DBT_PROJECT_DIR,
    ENV_JWKS_URL,
    ENV_JWT_AUDIENCE,
    ENV_JWT_ISSUER,
    ENV_JWT_SECRET,
    ENV_LLM_FALLBACKS,
    ENV_LLM_MODEL,
    ENV_LLM_REASONING_EFFORT,
    ENV_LLM_TIMEOUT,
    ENV_RATE_LIMIT,
    ENV_WAREHOUSE_PATH,
    ENV_WORKSPACE_ID,
    ENV_WORKSPACE_ROOT,
    LLM_DEFAULT_TIMEOUT_SECONDS,
)
from truemetric.interfaces import IAgentRunner, IQuestionParser, ITokenVerifier
from truemetric.repositories import ControlPlaneRepositoryContainer, JwtVerifier, RepositoryContainer
from truemetric.schemas import ControlPlaneSettings, LLMSettings, WorkspaceConfig
from truemetric.services import CachedAgentRunner, ControlPlaneServiceContainer, ServiceContainer
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


def build_agent(config: WorkspaceConfig) -> AgentGraph:
    """
    #Feature: Composition root
    #Scenario: Agent for one workspace, as the control plane's agent runner builds it
    #Complexity: Time O(engine startup)

    Args:
        config: Workspace settings.

    Returns:
        The workspace's agent.
    """
    try:
        return build_services(config).agent
    except Exception as exc:
        logger.error("build_agent failed: %s", exc, extra={"tenant_id": config.workspace_id})
        raise


def control_plane_settings_from_env() -> ControlPlaneSettings:
    """
    #Feature: Composition root
    #Scenario: API settings from TRUEMETRIC_* environment variables
    #Complexity: Time O(1)

    Returns:
        ControlPlaneSettings.

    Raises:
        ValueError: When TRUEMETRIC_DATABASE_URL is missing.
    """
    try:
        if not os.environ.get(ENV_DATABASE_URL):
            raise ValueError(f"[control_plane_settings_from_env] {ENV_DATABASE_URL} is not set. "
                             "Fix: export a postgresql+asyncpg:// URL for the truemetric_app role.")
        env = os.environ.get
        return ControlPlaneSettings(database_url=env(ENV_DATABASE_URL), jwt_secret=env(ENV_JWT_SECRET) or None,
                                    jwks_url=env(ENV_JWKS_URL) or None, jwt_audience=env(ENV_JWT_AUDIENCE) or None,
                                    jwt_issuer=env(ENV_JWT_ISSUER) or None,
                                    rate_limit_per_minute=int(env(ENV_RATE_LIMIT, "60")),
                                    workspace_root=Path(env(ENV_WORKSPACE_ROOT, ".")), llm=llm_settings_from_env())
    except Exception as exc:
        logger.error("control_plane_settings_from_env failed: %s", exc)
        raise


class ControlPlaneRuntime:
    """
    #Feature: Composition root
    #Scenario: Process-wide control-plane dependencies, and per-request containers built from them
    #Complexity: Time O(1) per request
    """

    def __init__(self, settings: ControlPlaneSettings, engine: AsyncEngine,
                 sessionmaker: async_sessionmaker[AsyncSession], verifier: ITokenVerifier,
                 runner: IAgentRunner) -> None:
        """
        #Feature: Composition root
        #Scenario: Hold the database engine, token verifier and agent runner for the process
        #Complexity: Time O(1)

        Args:
            settings: Control-plane settings.
            engine: Async database engine.
            sessionmaker: Session factory.
            verifier: Token verifier.
            runner: Agent runner.
        """
        try:
            self.settings, self.engine, self.sessionmaker = settings, engine, sessionmaker
            self._verifier, self._runner = verifier, runner
        except Exception as exc:
            logger.error("ControlPlaneRuntime init failed: %s", exc)
            raise

    def services_for(self, session: AsyncSession) -> ControlPlaneServiceContainer:
        """
        #Feature: Composition root
        #Scenario: Wire one request's repositories into its services
        #Complexity: Time O(1)

        Args:
            session: Request-scoped session.

        Returns:
            Request-scoped service container.
        """
        try:
            return ControlPlaneServiceContainer(self.settings, ControlPlaneRepositoryContainer(session),
                                                self._verifier, self._runner)
        except Exception as exc:
            logger.error("services_for failed: %s", exc)
            raise


def build_control_plane(settings: ControlPlaneSettings) -> ControlPlaneRuntime:
    """
    #Feature: Composition root
    #Scenario: Create the database engine, token verifier and cached agent runner once per process
    #Complexity: Time O(1); connections and agents are created lazily

    Args:
        settings: Control-plane settings.

    Returns:
        The runtime.

    Raises:
        ValueError: When settings is None.
    """
    try:
        if settings is None:
            raise ValueError("[build_control_plane] 'settings' is required.")
        engine = create_async_engine(settings.database_url, pool_pre_ping=True)
        verifier = JwtVerifier(settings.jwt_secret, settings.jwks_url, settings.jwt_audience, settings.jwt_issuer)
        runner = CachedAgentRunner(build_agent, settings.agent_cache_size)
        return ControlPlaneRuntime(settings, engine, async_sessionmaker(engine, expire_on_commit=False),
                                   verifier, runner)
    except Exception as exc:
        logger.error("build_control_plane failed: %s", exc)
        raise
