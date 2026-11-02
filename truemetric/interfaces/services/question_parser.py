from abc import ABC, abstractmethod
from datetime import date

from truemetric.schemas import MetricInfo, ParsedQuestion


class IQuestionParser(ABC):
    """
    #Feature: Agent routing
    #Scenario: Turn a plain-English question into intent and a candidate metric query
    #Complexity: Time O(1) per call, plus model latency
    """

    @abstractmethod
    def parse(self, question: str, catalog: list[MetricInfo], today: date) -> ParsedQuestion:
        """
        #Feature: Agent routing
        #Scenario: Parse one question against the workspace metric catalog
        #Complexity: Time O(question length * catalog size)

        Args:
            question: The user's question.
            catalog: Approved metrics with their dimensions.
            today: The workspace "today", for relative dates.

        Returns:
            The parsed question. Must not invent metrics outside the catalog.
        """
