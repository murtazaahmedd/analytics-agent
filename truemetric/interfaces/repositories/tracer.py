from abc import ABC, abstractmethod
from typing import Any


class ITracer(ABC):
    """
    #Feature: Observability
    #Scenario: Record every agent step for a question
    #Complexity: Time O(1) per event
    """

    @abstractmethod
    def start(self, workspace_id: str, question: str) -> str:
        """
        #Feature: Observability
        #Scenario: Open a trace for one question
        #Complexity: Time O(1)

        Args:
            workspace_id: Tenant id.
            question: The user's question.

        Returns:
            New trace id.
        """

    @abstractmethod
    def event(self, trace_id: str, name: str, payload: dict[str, Any]) -> None:
        """
        #Feature: Observability
        #Scenario: Record one step within a trace
        #Complexity: Time O(1)

        Args:
            trace_id: Trace id from start.
            name: Step name.
            payload: JSON-serialisable step data.
        """
