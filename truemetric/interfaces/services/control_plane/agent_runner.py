from abc import ABC, abstractmethod

from truemetric.schemas import AgentAnswer, WorkspaceConfig


class IAgentRunner(ABC):
    """
    #Feature: Ask in plain English
    #Scenario: Run the agent for any workspace, reusing its loaded engine (Abstract Factory over AgentGraph)
    #Complexity: Time O(agent) per question; O(engine startup) the first time a workspace is seen
    """

    @abstractmethod
    def run(self, config: WorkspaceConfig, question: str) -> AgentAnswer:
        """
        #Feature: Ask in plain English
        #Scenario: Answer one question with the workspace's agent (blocking; call from a worker thread)
        #Complexity: Time O(agent)

        Args:
            config: Workspace runtime settings.
            question: The question.

        Returns:
            The agent's answer.
        """
