import json
import logging
import threading
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from truemetric.interfaces import ITracer
from truemetric.utilities import require

logger = logging.getLogger(__name__)


class JsonlTracer(ITracer):
    """
    #Feature: Observability
    #Scenario: Append-only JSONL trace per workspace (local stand-in until Langfuse is wired)
    #Complexity: Time O(1) per event
    """

    def __init__(self, trace_dir: Path) -> None:
        """
        #Feature: Observability
        #Scenario: Write traces under trace_dir/<workspace_id>.jsonl
        #Complexity: Time O(1)

        Args:
            trace_dir: Directory for trace files.
        """
        try:
            self._dir = Path(trace_dir)
            self._dir.mkdir(parents=True, exist_ok=True)
            self._workspaces: dict[str, str] = {}
            self._lock = threading.Lock()
        except Exception as exc:
            logger.error("JsonlTracer init failed: %s", exc)
            raise

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

        Raises:
            ValueError: When an argument is None.
        """
        try:
            require("JsonlTracer.start", workspace_id=(workspace_id, str), question=(question, str))
            trace_id = uuid.uuid4().hex
            self._workspaces[trace_id] = workspace_id
            self.event(trace_id, "question", {"question": question})
            return trace_id
        except Exception as exc:
            logger.error("start failed: %s", exc, extra={"tenant_id": workspace_id})
            raise

    def event(self, trace_id: str, name: str, payload: dict[str, Any]) -> None:
        """
        #Feature: Observability
        #Scenario: Append one step to the workspace's trace file
        #Complexity: Time O(payload)

        Args:
            trace_id: Trace id from start.
            name: Step name.
            payload: JSON-serialisable step data.
        """
        try:
            workspace_id = self._workspaces.get(trace_id, "unknown")
            record = {"ts": datetime.now(UTC).isoformat(), "trace_id": trace_id, "workspace_id": workspace_id,
                      "event": name, "payload": payload}
            with self._lock, (self._dir / f"{workspace_id}.jsonl").open("a") as handle:
                handle.write(json.dumps(record, default=str) + "\n")
        except Exception as exc:
            logger.error("event failed: %s", exc, extra={"session_id": trace_id})
            raise
