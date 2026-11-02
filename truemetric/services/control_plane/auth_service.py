import logging
from uuid import UUID

from truemetric.errors import Errors
from truemetric.interfaces import IAuthRepository, IAuthService, ITokenVerifier
from truemetric.schemas import AuthContext

logger = logging.getLogger(__name__)


class AuthService(IAuthService):
    """
    #Feature: Access control
    #Scenario: Token -> user -> api.enforce, once per request
    #Complexity: Time O(1) per request
    """

    def __init__(self, verifier: ITokenVerifier, repository: IAuthRepository, rate_limit: int) -> None:
        """
        #Feature: Access control
        #Scenario: Inject the token verifier, the auth repository and the per-user rate limit
        #Complexity: Time O(1)

        Args:
            verifier: Token verifier.
            repository: Users and enforcement.
            rate_limit: Requests per minute per user.
        """
        try:
            self._verifier, self._repository, self._rate_limit = verifier, repository, rate_limit
        except Exception as exc:
            logger.error("AuthService init failed: %s", exc)
            raise

    async def authorize(self, token: str | None, workspace_id: UUID | None, permission: str) -> AuthContext:
        """
        #Feature: Access control
        #Scenario: Verify, register, enforce
        #Complexity: Time O(1)
        """
        if permission is None:
            raise ValueError("[AuthService.authorize] 'permission' is required.")
        try:
            if not token:
                raise Errors.HTTP.Unauthorized("[AuthService.authorize] Missing bearer token. "
                                               "Fix: send 'Authorization: Bearer <token>'.")
            claims = self._verifier.verify(token)
            user_id = await self._repository.upsert_user(claims)
            role = await self._repository.enforce(user_id, workspace_id, permission, self._rate_limit)
            return AuthContext(user_id=user_id, email=claims.email, role=role, workspace_id=workspace_id)
        except Exception as exc:
            logger.warning("authorize denied %s: %s", permission, exc, extra={"tenant_id": str(workspace_id)})
            raise
