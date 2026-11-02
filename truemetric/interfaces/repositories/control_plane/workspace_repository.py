from abc import ABC, abstractmethod
from datetime import datetime
from uuid import UUID

from truemetric.schemas import MemberOut, MemberRole, WorkspaceOut, WorkspaceRecord


class IWorkspaceRepository(ABC):
    """
    #Feature: Workspaces
    #Scenario: Workspaces and memberships in the control-plane database
    #Complexity: Time O(1) per call
    """

    @abstractmethod
    async def create(self, user_id: UUID, name: str, dbt_project_dir: str, warehouse_path: str,
                     as_of: datetime | None) -> WorkspaceOut:
        """
        #Feature: Workspaces
        #Scenario: Create a workspace with the caller as owner
        #Complexity: Time O(1)

        Args:
            user_id: Creator.
            name: Display name.
            dbt_project_dir: Resolved metric repo path.
            warehouse_path: Resolved warehouse path.
            as_of: Optional pinned clock.

        Returns:
            The new workspace.
        """

    @abstractmethod
    async def list_for_user(self, user_id: UUID) -> list[WorkspaceOut]:
        """
        #Feature: Workspaces
        #Scenario: Workspaces the user belongs to
        #Complexity: Time O(workspaces)

        Args:
            user_id: Caller.

        Returns:
            Workspaces, newest first.
        """

    @abstractmethod
    async def get(self, workspace_id: UUID) -> WorkspaceRecord:
        """
        #Feature: Workspaces
        #Scenario: Runtime settings of the enforced workspace
        #Complexity: Time O(1)

        Args:
            workspace_id: Workspace id.

        Returns:
            The workspace record.

        Raises:
            Errors.HTTP.NotFound: When row-level security hides it or it does not exist.
        """

    @abstractmethod
    async def add_member(self, workspace_id: UUID, email: str, role: MemberRole) -> MemberOut:
        """
        #Feature: Workspaces
        #Scenario: Add an existing user to the enforced workspace
        #Complexity: Time O(1)

        Args:
            workspace_id: Workspace id.
            email: The user's email.
            role: Role to grant.

        Returns:
            The membership.

        Raises:
            Errors.HTTP.NotFound: When no user has that email.
            Errors.Database.IntegrityError: When the user is already a member.
        """
