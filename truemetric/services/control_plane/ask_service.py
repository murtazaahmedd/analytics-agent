import asyncio
import logging
import time

from truemetric.interfaces import IAgentRunner, IAskRunRepository, IAskService, IWorkspaceRepository
from truemetric.schemas import AgentAnswer, AskRunOut, AuthContext, LLMSettings, WorkspaceConfig, WorkspaceRecord

logger = logging.getLogger(__name__)


def workspace_config(record: WorkspaceRecord, llm: LLMSettings | None) -> WorkspaceConfig:
    """
    #Feature: Ask in plain English
    #Scenario: Runtime settings for the agent from a control-plane workspace row
    #Complexity: Time O(1)

    Args:
        record: Workspace row.
        llm: Router model settings, or None for the rule-based router.

    Returns:
        WorkspaceConfig keyed by the workspace id (also the trace file name).
    """
    try:
        return WorkspaceConfig(workspace_id=str(record.id), dbt_project_dir=record.dbt_project_dir,
                               duckdb_path=record.warehouse_path, as_of=record.as_of, llm=llm)
    except Exception as exc:
        logger.error("workspace_config failed: %s", exc, extra={"tenant_id": str(record.id)})
        raise


class AskService(IAskService):
    """
    #Feature: Ask in plain English
    #Scenario: Load the workspace, run its agent off the event loop, record the outcome
    #Complexity: Time O(agent) per question
    """

    def __init__(self, workspaces: IWorkspaceRepository, ask_runs: IAskRunRepository, runner: IAgentRunner,
                 llm: LLMSettings | None) -> None:
        """
        #Feature: Ask in plain English
        #Scenario: Inject repositories, the agent runner and router model settings
        #Complexity: Time O(1)

        Args:
            workspaces: Workspace repository.
            ask_runs: Audit log repository.
            runner: Agent runner.
            llm: Router model settings, or None.
        """
        try:
            self._workspaces, self._ask_runs, self._runner, self._llm = workspaces, ask_runs, runner, llm
        except Exception as exc:
            logger.error("AskService init failed: %s", exc)
            raise

    async def ask(self, auth: AuthContext, question: str) -> AgentAnswer:
        """
        #Feature: Ask in plain English
        #Scenario: Answer and audit one question
        #Complexity: Time O(agent)
        """
        if auth is None or question is None or auth.workspace_id is None:
            raise ValueError("[AskService.ask] 'auth' bound to a workspace and 'question' are required.")
        tenant = {"tenant_id": str(auth.workspace_id)}
        try:
            config = workspace_config(await self._workspaces.get(auth.workspace_id), self._llm)
            started = time.perf_counter()
            answer = await asyncio.to_thread(self._runner.run, config, question)
            latency_ms = round((time.perf_counter() - started) * 1000)
            await self._ask_runs.record(auth.workspace_id, auth.user_id, question, answer, latency_ms)
            logger.info("question answered: %s", answer.outcome.value, extra={**tenant, "session_id": answer.trace_id})
            return answer
        except Exception as exc:
            logger.error("ask failed: %s", exc, extra=tenant)
            raise

    async def history(self, auth: AuthContext, page: int, limit: int) -> list[AskRunOut]:
        """
        #Feature: Audit log
        #Scenario: One page of the workspace's questions
        #Complexity: Time O(limit)
        """
        if auth is None or page is None or limit is None or auth.workspace_id is None:
            raise ValueError("[AskService.history] 'auth' bound to a workspace, 'page' and 'limit' are required.")
        try:
            return await self._ask_runs.list(auth.workspace_id, limit, (page - 1) * limit)
        except Exception as exc:
            logger.error("history failed: %s", exc, extra={"tenant_id": str(auth.workspace_id)})
            raise
