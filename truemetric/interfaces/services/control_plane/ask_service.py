from abc import ABC, abstractmethod

from truemetric.schemas import AgentAnswer, AskRunOut, AuthContext


class IAskService(ABC):
    """
    #Feature: Ask in plain English
    #Scenario: Run the agent for a workspace and keep an audit trail
    #Complexity: Time O(agent) per question
    """

    @abstractmethod
    async def ask(self, auth: AuthContext, question: str) -> AgentAnswer:
        """
        #Feature: Ask in plain English
        #Scenario: Answer one question in the caller's workspace and record it
        #Complexity: Time O(agent)

        Args:
            auth: Authorised caller, bound to a workspace.
            question: The question.

        Returns:
            The agent's answer.
        """

    @abstractmethod
    async def history(self, auth: AuthContext, page: int, limit: int) -> list[AskRunOut]:
        """
        #Feature: Audit log
        #Scenario: One page of questions asked in the caller's workspace
        #Complexity: Time O(limit)

        Args:
            auth: Authorised caller, bound to a workspace.
            page: 1-based page number.
            limit: Page size.

        Returns:
            Audit rows, newest first.
        """
