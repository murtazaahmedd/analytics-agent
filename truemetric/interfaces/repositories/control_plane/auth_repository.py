from abc import ABC, abstractmethod
from uuid import UUID

from truemetric.schemas import Role, TokenClaims


class IAuthRepository(ABC):
    """
    #Feature: Access control
    #Scenario: Users and per-request enforcement in the control-plane database
    #Complexity: Time O(1) per call
    """

    @abstractmethod
    async def upsert_user(self, claims: TokenClaims) -> UUID:
        """
        #Feature: Authentication
        #Scenario: Create the user on first sign-in; keep the email current
        #Complexity: Time O(1)

        Args:
            claims: Verified token claims.

        Returns:
            The user id.
        """

    @abstractmethod
    async def enforce(self, user_id: UUID, workspace_id: UUID | None, permission: str, rate_limit: int) -> Role | None:
        """
        #Feature: Access control
        #Scenario: Rate limit, RBAC and row-level-security binding in one api.enforce call
        #Complexity: Time O(1)

        Args:
            user_id: Caller.
            workspace_id: Workspace the request targets, or None.
            permission: resource.action permission.
            rate_limit: Requests allowed per minute.

        Returns:
            The caller's role in the workspace, or None when no workspace is targeted.

        Raises:
            Errors.HTTP.Forbidden: When the caller is not allowed.
            Errors.Misc.RateLimitExceeded: When the caller is over the limit.
        """
