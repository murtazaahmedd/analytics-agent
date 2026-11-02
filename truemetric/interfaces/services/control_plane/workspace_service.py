from abc import ABC, abstractmethod

from truemetric.schemas import AuthContext, MemberAdd, MemberOut, WorkspaceCreate, WorkspaceOut


class IWorkspaceService(ABC):
    """
    #Feature: Workspaces
    #Scenario: Create, list and share workspaces
    #Complexity: Time O(1) per call
    """

    @abstractmethod
    async def create(self, auth: AuthContext, request: WorkspaceCreate) -> WorkspaceOut:
        """
        #Feature: Workspaces
        #Scenario: Create a workspace on a metric repo and warehouse inside the workspace root
        #Complexity: Time O(path depth)

        Args:
            auth: Authorised caller.
            request: Workspace settings.

        Returns:
            The new workspace, with the caller as owner.

        Raises:
            Errors.HTTP.BadRequest: When a path is missing or outside the workspace root.
        """

    @abstractmethod
    async def list(self, auth: AuthContext) -> list[WorkspaceOut]:
        """
        #Feature: Workspaces
        #Scenario: Workspaces the caller belongs to
        #Complexity: Time O(workspaces)

        Args:
            auth: Authorised caller.

        Returns:
            Workspaces, newest first.
        """

    @abstractmethod
    async def add_member(self, auth: AuthContext, request: MemberAdd) -> MemberOut:
        """
        #Feature: Workspaces
        #Scenario: An owner adds a user to their workspace
        #Complexity: Time O(1)

        Args:
            auth: Authorised owner, bound to a workspace.
            request: Email and role.

        Returns:
            The membership.
        """
