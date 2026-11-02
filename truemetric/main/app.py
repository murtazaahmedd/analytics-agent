import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from truemetric.composition import build_control_plane, control_plane_settings_from_env
from truemetric.routers import asks_router, workspaces_router
from truemetric.schemas import ControlPlaneSettings

logger = logging.getLogger(__name__)


async def health() -> dict[str, str]:
    """
    #Feature: Control plane
    #Scenario: GET /health - liveness probe for Cloud Run (no auth, no database)
    #Complexity: Time O(1)
    """
    return {"status": "ok"}


def create_app(settings: ControlPlaneSettings | None = None) -> FastAPI:
    """
    #Feature: Control plane
    #Scenario: Build the API; settings come from the environment unless passed in (tests)
    #Complexity: Time O(routes)

    Args:
        settings: Optional settings override.

    Returns:
        The FastAPI app. The runtime (engine, verifier, agent runner) is built on startup.
    """

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        """
        #Feature: Control plane
        #Scenario: Build the runtime on startup, close database connections on shutdown
        #Complexity: Time O(1)
        """
        runtime = build_control_plane(settings or control_plane_settings_from_env())
        app.state.runtime = runtime
        try:
            yield
        finally:
            await runtime.engine.dispose()

    try:
        app = FastAPI(title="TrueMetric", version="0.2.0", lifespan=lifespan)
        app.add_api_route("/health", health, methods=["GET"])
        app.include_router(workspaces_router)
        app.include_router(asks_router)
        return app
    except Exception as exc:
        logger.error("create_app failed: %s", exc)
        raise
