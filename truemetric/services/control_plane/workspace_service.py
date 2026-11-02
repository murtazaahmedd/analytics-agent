import logging
from pathlib import Path

from truemetric.interfaces import IWorkspaceRepository, IWorkspaceService
from truemetric.schemas import AuthContext, MemberAdd, MemberOut, WorkspaceCreate, WorkspaceOut
from truemetric.utilities import naive_utc, resolve_inside

logger = logging.getLogger(__name__)


class WorkspaceService(IWorkspaceService):
    """
    #Feature: Workspaces
    #Scenario: Create, list and share workspaces; paths are bounded to the workspace root
    #Complexity: Time O(1) per call
    """

    def __init__(self, repository: IWorkspaceRepository, workspace_root: Path) -> None:
        """
        #Feature: Workspaces
        #Scenario: Inject the workspace repository and the allowed root for workspace files
        #Complexity: Time O(1)

        Args:
            repository: Workspaces and memberships.
            workspace_root: Directory every metric repo and warehouse file must live under.
        """
        try:
            self._repository, self._root = repository, workspace_root
        except Exception as exc:
            logger.error("WorkspaceService init failed: %s", exc)
            raise

    async def create(self, auth: AuthContext, request: WorkspaceCreate) -> WorkspaceOut:
        """
        #Feature: Workspaces
        #Scenario: Validate both paths, then create with the caller as owner
        #Complexity: Time O(path depth)
        """
        if auth is None or request is None:
            raise ValueError("[WorkspaceService.create] 'auth' and 'request' are required.")
        try:
            dbt_dir = resolve_inside(request.dbt_project_dir, self._root)
            warehouse = resolve_inside(request.warehouse_path, self._root)
            created = await self._repository.create(auth.user_id, request.name, str(dbt_dir), str(warehouse),
                                                    naive_utc(request.as_of))
            logger.info("workspace created", extra={"tenant_id": str(created.id)})
            return created
        except Exception as exc:
            logger.warning("create failed: %s", exc)
            raise

    async def list(self, auth: AuthContext) -> list[WorkspaceOut]:
        """
        #Feature: Workspaces
        #Scenario: The caller's workspaces
        #Complexity: Time O(workspaces)
        """
        if auth is None:
            raise ValueError("[WorkspaceService.list] 'auth' is required.")
        try:
            return await self._repository.list_for_user(auth.user_id)
        except Exception as exc:
            logger.error("list failed: %s", exc)
            raise

    async def add_member(self, auth: AuthContext, request: MemberAdd) -> MemberOut:
        """
        #Feature: Workspaces
        #Scenario: Owner adds a user
        #Complexity: Time O(1)
        """
        if auth is None or request is None or auth.workspace_id is None:
            raise ValueError("[WorkspaceService.add_member] 'auth' bound to a workspace and 'request' are required.")
        try:
            return await self._repository.add_member(auth.workspace_id, request.email, request.role)
        except Exception as exc:
            logger.warning("add_member failed: %s", exc, extra={"tenant_id": str(auth.workspace_id)})
            raise
