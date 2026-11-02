import logging
from datetime import datetime
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from truemetric.interfaces import IWorkspaceRepository
from truemetric.schemas import MemberOut, MemberRole, WorkspaceOut, WorkspaceRecord
from truemetric.utilities import translate_db_error

logger = logging.getLogger(__name__)


class PostgresWorkspaceRepository(IWorkspaceRepository):
    """
    #Feature: Workspaces
    #Scenario: Workspace and membership UDFs on the request's transaction
    #Complexity: Time O(1) per call
    """

    def __init__(self, session: AsyncSession) -> None:
        """
        #Feature: Workspaces
        #Scenario: Bind to the request-scoped session
        #Complexity: Time O(1)

        Args:
            session: Request-scoped async session.
        """
        try:
            self._session = session
        except Exception as exc:
            logger.error("PostgresWorkspaceRepository init failed: %s", exc)
            raise

    async def create(self, user_id: UUID, name: str, dbt_project_dir: str, warehouse_path: str,
                     as_of: datetime | None) -> WorkspaceOut:
        """
        #Feature: Workspaces
        #Scenario: api.create_workspace
        #Complexity: Time O(1)
        """
        try:
            result = await self._session.execute(
                text("select * from api.create_workspace(:user_id, :name, :dbt_dir, :warehouse, :as_of)"),
                {"user_id": user_id, "name": name, "dbt_dir": dbt_project_dir, "warehouse": warehouse_path,
                 "as_of": as_of})
            return WorkspaceOut.model_validate(dict(result.mappings().one()))
        except Exception as exc:
            logger.error("create failed: %s", exc)
            raise translate_db_error(exc, "PostgresWorkspaceRepository.create") from exc

    async def list_for_user(self, user_id: UUID) -> list[WorkspaceOut]:
        """
        #Feature: Workspaces
        #Scenario: api.list_workspaces
        #Complexity: Time O(workspaces)
        """
        try:
            result = await self._session.execute(text("select * from api.list_workspaces(:user_id)"),
                                                 {"user_id": user_id})
            return [WorkspaceOut.model_validate(dict(row)) for row in result.mappings()]
        except Exception as exc:
            logger.error("list_for_user failed: %s", exc)
            raise translate_db_error(exc, "PostgresWorkspaceRepository.list_for_user") from exc

    async def get(self, workspace_id: UUID) -> WorkspaceRecord:
        """
        #Feature: Workspaces
        #Scenario: api.get_workspace
        #Complexity: Time O(1)
        """
        try:
            result = await self._session.execute(text("select * from api.get_workspace(:workspace_id)"),
                                                 {"workspace_id": workspace_id})
            return WorkspaceRecord.model_validate(dict(result.mappings().one()))
        except Exception as exc:
            logger.error("get failed: %s", exc, extra={"tenant_id": str(workspace_id)})
            raise translate_db_error(exc, "PostgresWorkspaceRepository.get") from exc

    async def add_member(self, workspace_id: UUID, email: str, role: MemberRole) -> MemberOut:
        """
        #Feature: Workspaces
        #Scenario: api.add_member
        #Complexity: Time O(1)
        """
        try:
            result = await self._session.execute(text("select * from api.add_member(:workspace_id, :email, :role)"),
                                                 {"workspace_id": workspace_id, "email": email, "role": role.value})
            return MemberOut.model_validate(dict(result.mappings().one()))
        except Exception as exc:
            logger.error("add_member failed: %s", exc, extra={"tenant_id": str(workspace_id)})
            raise translate_db_error(exc, "PostgresWorkspaceRepository.add_member") from exc
