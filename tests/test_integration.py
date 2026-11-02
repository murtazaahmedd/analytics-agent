from datetime import datetime
from pathlib import Path

import pytest

from truemetric.agent import AgentGraph
from truemetric.composition import build_services
from truemetric.schemas import Outcome, WorkspaceConfig


@pytest.fixture(scope="module")
def agent(root: Path, warehouse_path: Path) -> AgentGraph:
    """
    #Feature: Test fixtures
    #Scenario: Real agent on the demo warehouse with a pinned clock and the rule-based router
    #Complexity: Time O(engine startup)
    """
    config = WorkspaceConfig(workspace_id="itest", dbt_project_dir=root / "demo_workspaces/thelook",
                             duckdb_path=warehouse_path, as_of=datetime(2026, 11, 1), trace_dir=root / "traces/tests")
    return build_services(config).agent


def test_end_to_end_answer(agent: AgentGraph) -> None:
    """
    #Feature: Ask in plain English
    #Scenario: A real question returns a number, the metric definition and the SQL
    #Complexity: Time O(query)
    """
    answer = agent.ask("What was net revenue in March 2024?")
    assert answer.outcome == Outcome.ANSWERED
    assert answer.metric == "net_revenue" and answer.sql and len(answer.rows) == 1


def test_month_only_metric_gets_month_grain(agent: AgentGraph) -> None:
    """
    #Feature: Semantic layer
    #Scenario: Repeat purchase rate is never aggregated across months
    #Complexity: Time O(query)
    """
    answer = agent.ask("Repeat purchase rate in Q1 2026")
    assert answer.outcome == Outcome.ANSWERED and len(answer.rows) == 3
