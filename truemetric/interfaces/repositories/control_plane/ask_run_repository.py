from abc import ABC, abstractmethod
from uuid import UUID

from truemetric.schemas import AgentAnswer, AskRunOut


class IAskRunRepository(ABC):
    """
    #Feature: Audit log
    #Scenario: Every question asked in a workspace and its outcome
    #Complexity: Time O(1) per write
    """

    @abstractmethod
    async def record(self, workspace_id: UUID, user_id: UUID, question: str, answer: AgentAnswer,
                     latency_ms: int) -> UUID:
        """
        #Feature: Audit log
        #Scenario: Append one question to the enforced workspace's log
        #Complexity: Time O(1)

        Args:
            workspace_id: Workspace id.
            user_id: Who asked.
            question: The question.
            answer: The agent's answer.
            latency_ms: End-to-end agent time.

        Returns:
            The audit row id.
        """

    @abstractmethod
    async def list(self, workspace_id: UUID, limit: int, offset: int) -> list[AskRunOut]:
        """
        #Feature: Audit log
        #Scenario: One page of the enforced workspace's log
        #Complexity: Time O(limit)

        Args:
            workspace_id: Workspace id.
            limit: Page size.
            offset: Rows to skip.

        Returns:
            Audit rows, newest first.
        """
