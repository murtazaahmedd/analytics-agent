import logging

from sqlalchemy.ext.asyncio import AsyncSession

from truemetric.interfaces import IAskRunRepository, IAuthRepository, IWorkspaceRepository
from truemetric.repositories.control_plane.ask_run_repository import PostgresAskRunRepository
from truemetric.repositories.control_plane.auth_repository import PostgresAuthRepository
from truemetric.repositories.control_plane.workspace_repository import PostgresWorkspaceRepository

logger = logging.getLogger(__name__)


class ControlPlaneRepositoryContainer:
    """
    #Feature: Composition root
    #Scenario: Lazily created control-plane repositories sharing one request-scoped transaction
    #Complexity: Time O(1) per property after first access

    Request-scoped (unlike RepositoryContainer, which is per workspace), because api.enforce binds
    row-level security to the transaction every later UDF call runs in.
    """

    def __init__(self, session: AsyncSession) -> None:
        """
        #Feature: Composition root
        #Scenario: Hold the request's session; nothing is created until first use
        #Complexity: Time O(1)

        Args:
            session: Request-scoped async session.

        Raises:
            ValueError: When session is None.
        """
        try:
            if session is None:
                raise ValueError("[ControlPlaneRepositoryContainer.__init__] 'session' is required.")
            self._session = session
            self._auth: IAuthRepository | None = None
            self._workspaces: IWorkspaceRepository | None = None
            self._ask_runs: IAskRunRepository | None = None
        except Exception as exc:
            logger.error("ControlPlaneRepositoryContainer init failed: %s", exc)
            raise

    @property
    def auth(self) -> IAuthRepository:
        """
        #Feature: Composition root
        #Scenario: Users and enforcement
        #Complexity: Time O(1)
        """
        try:
            if self._auth is None:
                self._auth = PostgresAuthRepository(self._session)
            return self._auth
        except Exception as exc:
            logger.error("auth failed: %s", exc)
            raise

    @property
    def workspaces(self) -> IWorkspaceRepository:
        """
        #Feature: Composition root
        #Scenario: Workspaces and memberships
        #Complexity: Time O(1)
        """
        try:
            if self._workspaces is None:
                self._workspaces = PostgresWorkspaceRepository(self._session)
            return self._workspaces
        except Exception as exc:
            logger.error("workspaces failed: %s", exc)
            raise

    @property
    def ask_runs(self) -> IAskRunRepository:
        """
        #Feature: Composition root
        #Scenario: Audit log
        #Complexity: Time O(1)
        """
        try:
            if self._ask_runs is None:
                self._ask_runs = PostgresAskRunRepository(self._session)
            return self._ask_runs
        except Exception as exc:
            logger.error("ask_runs failed: %s", exc)
            raise
