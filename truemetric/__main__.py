import argparse
import logging
import os
from datetime import datetime
from pathlib import Path

from truemetric.composition import build_services, llm_settings_from_env
from truemetric.constants import ENV_AS_OF
from truemetric.schemas import WorkspaceConfig

logger = logging.getLogger(__name__)


def main() -> None:
    """
    #Feature: Ask in plain English
    #Scenario: Ask the demo workspace one question from the terminal
    #Complexity: Time O(engine startup + query)
    """
    try:
        parser = argparse.ArgumentParser(description="Ask TrueMetric a question.")
        parser.add_argument("question")
        parser.add_argument("--project", type=Path, default=Path("demo_workspaces/thelook"))
        parser.add_argument("--warehouse", type=Path, default=Path("data/warehouse.duckdb"))
        parser.add_argument("--as-of", default=os.environ.get(ENV_AS_OF, "2026-11-01T00:00:00"))
        parser.add_argument("--show-sql", action="store_true")
        args = parser.parse_args()
        logging.basicConfig(level=logging.ERROR)
        config = WorkspaceConfig(workspace_id="demo", dbt_project_dir=args.project, duckdb_path=args.warehouse,
                                 as_of=datetime.fromisoformat(args.as_of), llm=llm_settings_from_env())
        agent = build_services(config).agent
        answer = agent.ask(args.question)
        print(f"[{answer.outcome.value}] {answer.text}\n\nTrace: {answer.trace_id}")
        if args.show_sql and answer.sql:
            print(f"\nSQL:\n{answer.sql}")
    except Exception as exc:
        logger.error("cli failed: %s", exc)
        raise


if __name__ == "__main__":
    main()
