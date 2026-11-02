from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, Field


class LLMSettings(BaseModel):
    """
    #Feature: LLM routing
    #Scenario: Which model routes questions, and how it is called
    #Complexity: Time O(1)

    reasoning_effort "disable" keeps Gemini Flash near 1 s per call; local CPU models need a long timeout.
    """

    model: str = Field(min_length=1)
    fallbacks: list[str] = Field(default_factory=list)
    reasoning_effort: str | None = None
    timeout_seconds: float = Field(default=20.0, gt=0)


class WorkspaceConfig(BaseModel):
    """
    #Feature: Workspaces
    #Scenario: Runtime settings for one customer workspace
    #Complexity: Time O(1)

    as_of pins "now" for relative dates and freshness; None means the current time.
    llm None means the deterministic rule-based router.
    """

    workspace_id: str = Field(min_length=1)
    dbt_project_dir: Path
    duckdb_path: Path
    as_of: datetime | None = None
    mart_schema: str = Field(default="analytics", pattern=r"^[A-Za-z_][A-Za-z0-9_]*$")
    max_result_rows: int = Field(default=5000, ge=1)
    trace_dir: Path = Path("traces")
    llm: LLMSettings | None = None
