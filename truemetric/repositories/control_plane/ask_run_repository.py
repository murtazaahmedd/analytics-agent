import logging
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from truemetric.interfaces import IAskRunRepository
from truemetric.schemas import AgentAnswer, AskRunOut
from truemetric.utilities import translate_db_error

logger = logging.getLogger(__name__)


class PostgresAskRunRepository(IAskRunRepository):
    """
    #Feature: Audit log
    #Scenario: api.record_ask and api.list_asks on the request's transaction
    #Complexity: Time O(1) per write
    """

    def __init__(self, session: AsyncSession) -> None:
        """
        #Feature: Audit log
        #Scenario: Bind to the request-scoped session
        #Complexity: Time O(1)

        Args:
            session: Request-scoped async session.
        """
        try:
            self._session = session
        except Exception as exc:
            logger.error("PostgresAskRunRepository init failed: %s", exc)
            raise

    async def record(self, workspace_id: UUID, user_id: UUID, question: str, answer: AgentAnswer,
                     latency_ms: int) -> UUID:
        """
        #Feature: Audit log
        #Scenario: api.record_ask
        #Complexity: Time O(1)
        """
        try:
            result = await self._session.execute(
                text("select api.record_ask(:workspace_id, :user_id, :question, :outcome, :metric, :trace_id, "
                     ":latency_ms)"),
                {"workspace_id": workspace_id, "user_id": user_id, "question": question,
                 "outcome": answer.outcome.value, "metric": answer.metric, "trace_id": answer.trace_id,
                 "latency_ms": latency_ms})
            return result.scalar_one()
        except Exception as exc:
            logger.error("record failed: %s", exc, extra={"tenant_id": str(workspace_id), "session_id": answer.trace_id})
            raise translate_db_error(exc, "PostgresAskRunRepository.record") from exc

    async def list(self, workspace_id: UUID, limit: int, offset: int) -> list[AskRunOut]:
        """
        #Feature: Audit log
        #Scenario: api.list_asks
        #Complexity: Time O(limit)
        """
        try:
            result = await self._session.execute(text("select * from api.list_asks(:workspace_id, :limit, :offset)"),
                                                 {"workspace_id": workspace_id, "limit": limit, "offset": offset})
            return [AskRunOut.model_validate(dict(row)) for row in result.mappings()]
        except Exception as exc:
            logger.error("list failed: %s", exc, extra={"tenant_id": str(workspace_id)})
            raise translate_db_error(exc, "PostgresAskRunRepository.list") from exc
