import logging
from uuid import UUID

from fastapi import APIRouter, Depends, Request

from truemetric.decorators import enforce, http_error_handler
from truemetric.routers.dependencies import get_services
from truemetric.schemas import MemberAdd, MemberOut, WorkspaceCreate, WorkspaceOut
from truemetric.services import ControlPlaneServiceContainer
from truemetric.utilities.auth_reforce import member, workspace

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


@router.post("", response_model=WorkspaceOut, status_code=201)
@http_error_handler
@enforce(workspace.create)
async def create_workspace(request: Request, payload: WorkspaceCreate,
                           services: ControlPlaneServiceContainer = Depends(get_services)) -> WorkspaceOut:
    """
    #Feature: Workspaces
    #Scenario: POST /workspaces - create a workspace; the caller becomes owner
    #Complexity: Time O(1)
    """
    try:
        return await services.workspaces.create(request.state.auth, payload)
    except Exception as exc:
        logger.warning("create_workspace failed: %s", exc)
        raise


@router.get("", response_model=list[WorkspaceOut])
@http_error_handler
@enforce(workspace.read)
async def list_workspaces(request: Request,
                          services: ControlPlaneServiceContainer = Depends(get_services)) -> list[WorkspaceOut]:
    """
    #Feature: Workspaces
    #Scenario: GET /workspaces - the caller's workspaces
    #Complexity: Time O(workspaces)
    """
    try:
        return await services.workspaces.list(request.state.auth)
    except Exception as exc:
        logger.warning("list_workspaces failed: %s", exc)
        raise


@router.post("/{workspace_id}/members", response_model=MemberOut, status_code=201)
@http_error_handler
@enforce(member.create)
async def add_member(request: Request, workspace_id: UUID, payload: MemberAdd,
                     services: ControlPlaneServiceContainer = Depends(get_services)) -> MemberOut:
    """
    #Feature: Workspaces
    #Scenario: POST /workspaces/{id}/members - an owner adds a user who has signed in before
    #Complexity: Time O(1)
    """
    try:
        return await services.workspaces.add_member(request.state.auth, payload)
    except Exception as exc:
        logger.warning("add_member failed: %s", exc, extra={"tenant_id": str(workspace_id)})
        raise
