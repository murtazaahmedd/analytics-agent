from datetime import datetime
from enum import Enum
from pathlib import Path
from uuid import UUID

from pydantic import BaseModel, Field

from truemetric.schemas.workspace_schemas import LLMSettings

EMAIL_PATTERN = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"


class Role(str, Enum):
    """
    #Feature: Access control
    #Scenario: A user's role in one workspace
    #Complexity: Time O(1)
    """

    OWNER = "owner"
    EDITOR = "editor"
    VIEWER = "viewer"


class MemberRole(str, Enum):
    """
    #Feature: Access control
    #Scenario: Roles an owner can grant (ownership is not transferable yet)
    #Complexity: Time O(1)
    """

    EDITOR = "editor"
    VIEWER = "viewer"


class TokenClaims(BaseModel):
    """
    #Feature: Authentication
    #Scenario: The identity a verified JWT carries
    #Complexity: Time O(1)
    """

    subject: str = Field(min_length=1, max_length=255)
    email: str = Field(pattern=EMAIL_PATTERN, max_length=320)


class AuthContext(BaseModel):
    """
    #Feature: Access control
    #Scenario: What @enforce puts on request.state.auth
    #Complexity: Time O(1)

    role and workspace_id are None for permissions that need no workspace.
    """

    user_id: UUID
    email: str
    role: Role | None = None
    workspace_id: UUID | None = None


class WorkspaceCreate(BaseModel):
    """
    #Feature: Workspaces
    #Scenario: Create a workspace on a metric repo and a warehouse
    #Complexity: Time O(1)

    as_of pins "now" for demo workspaces; leave it empty for real customers.
    """

    name: str = Field(min_length=1, max_length=100)
    dbt_project_dir: str = Field(min_length=1, max_length=500)
    warehouse_path: str = Field(min_length=1, max_length=500)
    as_of: datetime | None = None


class WorkspaceOut(BaseModel):
    """
    #Feature: Workspaces
    #Scenario: A workspace as listed to one of its members
    #Complexity: Time O(1)
    """

    id: UUID
    name: str
    role: Role
    as_of: datetime | None = None
    created_at: datetime


class WorkspaceRecord(BaseModel):
    """
    #Feature: Workspaces
    #Scenario: Runtime settings the agent needs for one workspace
    #Complexity: Time O(1)
    """

    id: UUID
    name: str
    dbt_project_dir: str
    warehouse_path: str
    as_of: datetime | None = None


class MemberAdd(BaseModel):
    """
    #Feature: Workspaces
    #Scenario: Invite an existing user into a workspace
    #Complexity: Time O(1)
    """

    email: str = Field(pattern=EMAIL_PATTERN, max_length=320)
    role: MemberRole = MemberRole.VIEWER


class MemberOut(BaseModel):
    """
    #Feature: Workspaces
    #Scenario: A membership that was just created
    #Complexity: Time O(1)
    """

    user_id: UUID
    email: str
    role: Role


class AskRunOut(BaseModel):
    """
    #Feature: Audit log
    #Scenario: One recorded question and its outcome
    #Complexity: Time O(1)
    """

    id: UUID
    user_email: str
    question: str
    outcome: str
    metric: str | None = None
    trace_id: str
    latency_ms: int
    created_at: datetime


class ControlPlaneSettings(BaseModel):
    """
    #Feature: Control plane
    #Scenario: Process-wide settings for the API
    #Complexity: Time O(1)

    Exactly one of jwt_secret (HS256, local and tests) or jwks_url (RS256/ES256 from Clerk, Firebase, Auth0)
    is expected. workspace_root bounds where workspace metric repos and warehouse files may live.
    """

    database_url: str = Field(min_length=1)
    jwt_secret: str | None = None
    jwks_url: str | None = None
    jwt_audience: str | None = None
    jwt_issuer: str | None = None
    rate_limit_per_minute: int = Field(default=60, ge=1)
    workspace_root: Path = Path(".")
    agent_cache_size: int = Field(default=8, ge=1)
    llm: LLMSettings | None = None
