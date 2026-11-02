import logging
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from truemetric.interfaces import IAuthRepository
from truemetric.schemas import Role, TokenClaims
from truemetric.utilities import translate_db_error

logger = logging.getLogger(__name__)


class PostgresAuthRepository(IAuthRepository):
    """
    #Feature: Access control
    #Scenario: api.upsert_user and api.enforce on the request's transaction
    #Complexity: Time O(1) per call
    """

    def __init__(self, session: AsyncSession) -> None:
        """
        #Feature: Access control
        #Scenario: Bind to the request-scoped session
        #Complexity: Time O(1)

        Args:
            session: Request-scoped async session.
        """
        try:
            self._session = session
        except Exception as exc:
            logger.error("PostgresAuthRepository init failed: %s", exc)
            raise

    async def upsert_user(self, claims: TokenClaims) -> UUID:
        """
        #Feature: Authentication
        #Scenario: Create the user on first sign-in
        #Complexity: Time O(1)
        """
        try:
            result = await self._session.execute(text("select api.upsert_user(:subject, :email)"),
                                                 {"subject": claims.subject, "email": claims.email})
            return result.scalar_one()
        except Exception as exc:
            logger.error("upsert_user failed: %s", exc)
            raise translate_db_error(exc, "PostgresAuthRepository.upsert_user") from exc

    async def enforce(self, user_id: UUID, workspace_id: UUID | None, permission: str, rate_limit: int) -> Role | None:
        """
        #Feature: Access control
        #Scenario: One api.enforce call per request
        #Complexity: Time O(1)
        """
        try:
            result = await self._session.execute(
                text("select role from api.enforce(:user_id, :workspace_id, :permission, :rate_limit)"),
                {"user_id": user_id, "workspace_id": workspace_id, "permission": permission,
                 "rate_limit": rate_limit})
            role = result.scalar_one()
            return Role(role) if role else None
        except Exception as exc:
            logger.warning("enforce denied: %s", exc, extra={"tenant_id": str(workspace_id)})
            raise translate_db_error(exc, "PostgresAuthRepository.enforce") from exc
