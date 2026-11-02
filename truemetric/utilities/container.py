import logging
from datetime import date, datetime

from truemetric.schemas import WorkspaceConfig

logger = logging.getLogger(__name__)


class UtilityContainer:
    """
    #Feature: Composition root
    #Scenario: Workspace clock injected into services (pinned by as_of in demos and evals)
    #Complexity: Time O(1)
    """

    def __init__(self, config: WorkspaceConfig) -> None:
        """
        #Feature: Composition root
        #Scenario: Bind the clock to the workspace's as_of
        #Complexity: Time O(1)

        Args:
            config: Workspace settings.

        Raises:
            ValueError: When config is None.
        """
        try:
            if config is None:
                raise ValueError("[UtilityContainer.__init__] 'config' is required.")
            self._as_of = config.as_of
        except Exception as exc:
            logger.error("UtilityContainer init failed: %s", exc)
            raise

    def now(self) -> datetime:
        """
        #Feature: Composition root
        #Scenario: Workspace "now"
        #Complexity: Time O(1)

        Returns:
            as_of when pinned, else the current time.
        """
        try:
            return self._as_of or datetime.now()
        except Exception as exc:
            logger.error("now failed: %s", exc)
            raise

    def today(self) -> date:
        """
        #Feature: Composition root
        #Scenario: Workspace "today", for relative dates
        #Complexity: Time O(1)

        Returns:
            Date part of now().
        """
        try:
            return self.now().date()
        except Exception as exc:
            logger.error("today failed: %s", exc)
            raise
