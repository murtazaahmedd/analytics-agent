import logging

from truemetric.interfaces import IAgentRunner, IAskService, IAuthService, ITokenVerifier, IWorkspaceService
from truemetric.repositories import ControlPlaneRepositoryContainer
from truemetric.schemas import ControlPlaneSettings
from truemetric.services.control_plane.ask_service import AskService
from truemetric.services.control_plane.auth_service import AuthService
from truemetric.services.control_plane.workspace_service import WorkspaceService

logger = logging.getLogger(__name__)


class ControlPlaneServiceContainer:
    """
    #Feature: Composition root
    #Scenario: Lazily wired control-plane services for one request
    #Complexity: Time O(1) per property after first access
    """

    def __init__(self, settings: ControlPlaneSettings, repositories: ControlPlaneRepositoryContainer,
                 verifier: ITokenVerifier, runner: IAgentRunner) -> None:
        """
        #Feature: Composition root
        #Scenario: Receive the request's repositories and the process-wide verifier and agent runner
        #Complexity: Time O(1)

        Args:
            settings: Control-plane settings.
            repositories: Request-scoped repository container.
            verifier: Token verifier.
            runner: Agent runner.

        Raises:
            ValueError: When a dependency is None.
        """
        try:
            if settings is None or repositories is None or verifier is None or runner is None:
                raise ValueError("[ControlPlaneServiceContainer.__init__] All dependencies are required.")
            self._settings, self._repositories, self._verifier, self._runner = settings, repositories, verifier, runner
            self._auth: IAuthService | None = None
            self._workspaces: IWorkspaceService | None = None
            self._asks: IAskService | None = None
        except Exception as exc:
            logger.error("ControlPlaneServiceContainer init failed: %s", exc)
            raise

    @property
    def auth(self) -> IAuthService:
        """
        #Feature: Composition root
        #Scenario: Authentication and enforcement
        #Complexity: Time O(1)
        """
        try:
            if self._auth is None:
                self._auth = AuthService(self._verifier, self._repositories.auth, self._settings.rate_limit_per_minute)
            return self._auth
        except Exception as exc:
            logger.error("auth failed: %s", exc)
            raise

    @property
    def workspaces(self) -> IWorkspaceService:
        """
        #Feature: Composition root
        #Scenario: Workspaces
        #Complexity: Time O(1)
        """
        try:
            if self._workspaces is None:
                self._workspaces = WorkspaceService(self._repositories.workspaces, self._settings.workspace_root)
            return self._workspaces
        except Exception as exc:
            logger.error("workspaces failed: %s", exc)
            raise

    @property
    def asks(self) -> IAskService:
        """
        #Feature: Composition root
        #Scenario: Asking and the audit log
        #Complexity: Time O(1)
        """
        try:
            if self._asks is None:
                self._asks = AskService(self._repositories.workspaces, self._repositories.ask_runs, self._runner,
                                        self._settings.llm)
            return self._asks
        except Exception as exc:
            logger.error("asks failed: %s", exc)
            raise
