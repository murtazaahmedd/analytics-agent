import logging
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request

from truemetric.constants import DEFAULT_PAGE_LIMIT, MAX_PAGE_LIMIT
from truemetric.decorators import enforce, http_error_handler
from truemetric.routers.dependencies import get_services
from truemetric.schemas import AgentAnswer, AskRequest, AskRunOut
from truemetric.services import ControlPlaneServiceContainer
from truemetric.utilities.auth_reforce import ask, audit

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/workspaces/{workspace_id}", tags=["asks"])


@router.post("/ask", response_model=AgentAnswer)
@http_error_handler
@enforce(ask.execute)
async def ask_question(request: Request, workspace_id: UUID, payload: AskRequest,
                       services: ControlPlaneServiceContainer = Depends(get_services)) -> AgentAnswer:
    """
    #Feature: Ask in plain English
    #Scenario: POST /workspaces/{id}/ask - answer through the workspace's metric layer and audit it
    #Complexity: Time O(agent)
    """
    try:
        return await services.asks.ask(request.state.auth, payload.question)
    except Exception as exc:
        logger.warning("ask_question failed: %s", exc, extra={"tenant_id": str(workspace_id)})
        raise


@router.get("/asks", response_model=list[AskRunOut])
@http_error_handler
@enforce(audit.read)
async def list_asks(request: Request, workspace_id: UUID, page: int = Query(1, ge=1),
                    limit: int = Query(DEFAULT_PAGE_LIMIT, ge=1, le=MAX_PAGE_LIMIT),
                    services: ControlPlaneServiceContainer = Depends(get_services)) -> list[AskRunOut]:
    """
    #Feature: Audit log
    #Scenario: GET /workspaces/{id}/asks - who asked what, and the outcome
    #Complexity: Time O(limit)
    """
    try:
        return await services.asks.history(request.state.auth, page, limit)
    except Exception as exc:
        logger.warning("list_asks failed: %s", exc, extra={"tenant_id": str(workspace_id)})
        raise
