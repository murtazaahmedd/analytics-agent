import logging
from collections.abc import AsyncIterator

from fastapi import Request

from truemetric.services import ControlPlaneServiceContainer

logger = logging.getLogger(__name__)


async def get_services(request: Request) -> AsyncIterator[ControlPlaneServiceContainer]:
    """
    #Feature: Composition root
    #Scenario: One session and transaction per request; api.enforce binds row-level security to it
    #Complexity: Time O(1) plus the request

    Commits when the endpoint finished. A transaction a failed UDF call aborted is rolled back instead
    (the endpoint already returned its error response).

    Args:
        request: Incoming request; the app's runtime is on request.app.state.runtime.

    Yields:
        Request-scoped service container.
    """
    runtime = request.app.state.runtime
    async with runtime.sessionmaker() as session:
        try:
            yield runtime.services_for(session)
        except Exception:
            await session.rollback()
            raise
        try:
            await session.commit()
        except Exception as exc:
            logger.info("transaction not committed (an earlier statement failed): %s", exc)
            await session.rollback()
