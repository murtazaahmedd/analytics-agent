from abc import ABC, abstractmethod
from uuid import UUID

from truemetric.schemas import AuthContext


class IAuthService(ABC):
    """
    #Feature: Access control
    #Scenario: Turn a bearer token plus a target workspace into an authorised context
    #Complexity: Time O(1) per request
    """

    @abstractmethod
    async def authorize(self, token: str | None, workspace_id: UUID | None, permission: str) -> AuthContext:
        """
        #Feature: Access control
        #Scenario: Verify the token, register the user, enforce the permission
        #Complexity: Time O(1)

        Args:
            token: Bearer token, or None when the header was missing.
            workspace_id: Workspace the request targets, or None.
            permission: resource.action permission.

        Returns:
            The authorised context.

        Raises:
            Errors.HTTP.Unauthorized: When the token is missing or invalid.
            Errors.HTTP.Forbidden: When the caller lacks the permission.
            Errors.Misc.RateLimitExceeded: When the caller is over the limit.
        """
