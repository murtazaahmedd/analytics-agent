"""Run the benchmark questions through the agent and grade them against hand-written SQL."""

import json
import logging
import statistics
import time
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel

from evals.faults import inject
from truemetric.agent import AgentGraph
from truemetric.composition import llm_settings_from_env
from truemetric.interfaces import IWarehouseConnector
from truemetric.schemas import AgentAnswer, Outcome, WorkspaceConfig
from truemetric.utilities import to_plain

logger = logging.getLogger("run_evals")

IN_SCOPE = {"simple", "sliced"}
RAW_SCHEMA = "thelook_ecommerce"
TRUTH_MAX_ROWS = 100_000

AgentForCase = Callable[["EvalCase"], AgentGraph]


class GateConfig(BaseModel):
    """
    #Feature: Evaluation
    #Scenario: Release gate thresholds
    #Complexity: Time O(1)
    """

    min_in_scope_accuracy: float
    max_confidently_wrong: int


class EvalConfig(BaseModel):
    """
    #Feature: Evaluation
    #Scenario: evals/config.yml
    #Complexity: Time O(1)
    """

    workspace_id: str
    dbt_project_dir: Path
    duckdb_path: Path
    fault_dir: Path
    as_of: datetime
    tolerance: float
    gate: GateConfig


class EvalSummary(BaseModel):
    """
    #Feature: Evaluation
    #Scenario: Headline numbers tracked on every run
    #Complexity: Time O(1)
    """

    total: int
    correct: int
    in_scope_accuracy: float
    confidently_wrong: int
    wrong_refusals: int
    bad_data_blocked: int
    reworded_accuracy: float | None
    routed_by_llm: int
    latency_p50_s: float | None
    latency_p95_s: float | None
    buckets: dict[str, str]


class EvalCase(BaseModel):
    """
    #Feature: Evaluation
    #Scenario: One benchmark question and its expected behaviour
    #Complexity: Time O(1)
    """

    id: str
    bucket: str
    question: str
    expect: Outcome
    sql: str | None = None
    ordered: bool = False
    fault: str | None = None
    failed_check: str | None = None


class EvalResult(BaseModel):
    """
    #Feature: Evaluation
    #Scenario: Grade for one question
    #Complexity: Time O(1)
    """

    id: str
    bucket: str
    question: str
    expected: Outcome
    outcome: Outcome
    correct: bool
    confidently_wrong: bool
    latency_s: float
    detail: str
    trace_id: str
    routed_by: str | None = None


def load_cases(directory: Path) -> list[EvalCase]:
    """
    #Feature: Evaluation
    #Scenario: Read every questions/*.yaml; the file name is the bucket
    #Complexity: Time O(cases)

    Args:
        directory: questions directory.

    Returns:
        Cases in file then list order.
    """
    try:
        cases = []
        for path in sorted(directory.glob("*.yaml")):
            cases += [EvalCase(bucket=path.stem, **raw) for raw in yaml.safe_load(path.read_text())]
        return cases
    except Exception as exc:
        logger.error("load_cases failed: %s", exc)
        raise


def expand_rewordings(cases: list[EvalCase], path: Path) -> list[EvalCase]:
    """
    #Feature: Evaluation
    #Scenario: Robustness - add reworded copies of in-scope cases, graded against the original SQL
    #Complexity: Time O(cases * rewordings)

    Args:
        cases: Base cases.
        path: rewordings.yaml mapping case id to alternative questions.

    Returns:
        Reworded cases in bucket "reworded"; ids are <id>.r<n>.
    """
    try:
        rewordings = yaml.safe_load(path.read_text())
        extra = []
        for case in cases:
            for n, question in enumerate(rewordings.get(case.id, []), start=1):
                extra.append(case.model_copy(update={"id": f"{case.id}.r{n}", "bucket": "reworded",
                                                     "question": question}))
        return extra
    except Exception as exc:
        logger.error("expand_rewordings failed: %s", exc)
        raise


def expected_rows(truth: IWarehouseConnector, sql: str) -> list[tuple]:
    """
    #Feature: Evaluation
    #Scenario: Ground truth from hand-written SQL on the clean warehouse's raw tables
    #Complexity: Time O(query)

    Args:
        truth: Read-only connector to the clean warehouse.
        sql: Expected-answer SQL; key columns first, value last.

    Returns:
        Rows of plain values.
    """
    try:
        return [tuple(to_plain(v) for v in row) for row in truth.execute(sql)[1]]
    except Exception as exc:
        logger.error("expected_rows failed: %s", exc)
        raise


def agent_rows(answer: AgentAnswer) -> list[tuple]:
    """
    #Feature: Evaluation
    #Scenario: Agent rows as (keys..., value) tuples in result order
    #Complexity: Time O(rows)

    Args:
        answer: Answered AgentAnswer.

    Returns:
        Rows with the metric value last.
    """
    try:
        keys = [c for c in answer.columns if c != answer.metric]
        return [tuple(row[k] for k in keys) + (row[answer.metric],) for row in answer.rows]
    except Exception as exc:
        logger.error("agent_rows failed: %s", exc)
        raise


def close(actual: Any, expected: Any, tolerance: float) -> bool:
    """
    #Feature: Evaluation
    #Scenario: Relative match within tolerance (0.5% by default)
    #Complexity: Time O(1)

    Args:
        actual: Agent value.
        expected: Ground-truth value.
        tolerance: Allowed relative error.

    Returns:
        True when both are None or within tolerance.
    """
    try:
        if actual is None or expected is None:
            return actual is None and expected is None
        return abs(float(actual) - float(expected)) <= max(tolerance * abs(float(expected)), 1e-9)
    except Exception as exc:
        logger.error("close failed: %s", exc)
        raise


def rows_match(actual: list[tuple], expected: list[tuple], ordered: bool, tolerance: float) -> tuple[bool, str]:
    """
    #Feature: Evaluation
    #Scenario: Compare keys exactly and values within tolerance; order matters for top-N questions
    #Complexity: Time O(rows log rows)

    Args:
        actual: Agent rows.
        expected: Ground-truth rows.
        ordered: Whether row order must match.
        tolerance: Relative tolerance.

    Returns:
        (match, detail).
    """
    try:
        if len(actual) != len(expected):
            return False, f"row count {len(actual)} != expected {len(expected)}"
        if not ordered:
            actual, expected = sorted(actual, key=str), sorted(expected, key=str)
        for got, want in zip(actual, expected):
            if [str(k) for k in got[:-1]] != [str(k) for k in want[:-1]] or not close(got[-1], want[-1], tolerance):
                return False, f"got {got} expected {want}"
        return True, f"{len(actual)} rows match"
    except Exception as exc:
        logger.error("rows_match failed: %s", exc)
        raise


def grade(case: EvalCase, answer: AgentAnswer, latency: float, truth: IWarehouseConnector,
          tolerance: float) -> EvalResult:
    """
    #Feature: Evaluation
    #Scenario: Grade one answer; any number that is not the expected number is confidently wrong
    #Complexity: Time O(query)

    Args:
        case: The case.
        answer: Agent answer.
        latency: Seconds taken.
        truth: Read-only connector to the clean warehouse.
        tolerance: Relative tolerance.

    Returns:
        EvalResult.
    """
    try:
        correct, detail = answer.outcome == case.expect, f"outcome {answer.outcome.value}"
        if correct and case.expect == Outcome.ANSWERED:
            correct, detail = rows_match(agent_rows(answer), expected_rows(truth, case.sql), case.ordered,
                                         tolerance)
        if correct and case.failed_check:
            failed = {c.check for c in answer.failed_checks}
            correct, detail = case.failed_check in failed, f"failed checks: {sorted(failed)}"
        wrong_number = answer.outcome == Outcome.ANSWERED and not correct
        return EvalResult(id=case.id, bucket=case.bucket, question=case.question, expected=case.expect,
                          outcome=answer.outcome, correct=correct, confidently_wrong=wrong_number,
                          latency_s=round(latency, 3), detail=detail, trace_id=answer.trace_id,
                          routed_by=answer.routed_by)
    except Exception as exc:
        logger.error("grade failed for case=%s: %s", case.id, exc)
        raise


def summarize(results: list[EvalResult]) -> EvalSummary:
    """
    #Feature: Evaluation
    #Scenario: Headline numbers tracked on every run
    #Complexity: Time O(results log results)

    Args:
        results: Graded results.

    Returns:
        EvalSummary.
    """
    try:
        in_scope = [r for r in results if r.bucket in IN_SCOPE]
        reworded = [r for r in results if r.bucket == "reworded"]
        latencies = sorted(r.latency_s for r in results if r.outcome == Outcome.ANSWERED)
        buckets = {b: f"{sum(r.correct for r in rs)}/{len(rs)}"
                   for b in dict.fromkeys(r.bucket for r in results) for rs in [[r for r in results if r.bucket == b]]}
        return EvalSummary(
            total=len(results), correct=sum(r.correct for r in results),
            in_scope_accuracy=sum(r.correct for r in in_scope) / len(in_scope) if in_scope else 0.0,
            confidently_wrong=sum(r.confidently_wrong for r in results),
            wrong_refusals=sum(1 for r in in_scope if r.outcome in (Outcome.REFUSED, Outcome.CLARIFY)),
            bad_data_blocked=sum(r.correct for r in results if r.bucket == "bad_data"),
            reworded_accuracy=sum(r.correct for r in reworded) / len(reworded) if reworded else None,
            routed_by_llm=sum(r.routed_by == "llm" for r in results),
            latency_p50_s=statistics.median(latencies) if latencies else None,
            latency_p95_s=latencies[int(0.95 * (len(latencies) - 1))] if latencies else None,
            buckets=buckets)
    except Exception as exc:
        logger.error("summarize failed: %s", exc)
        raise


def gate_passed(summary: EvalSummary, gate: GateConfig) -> bool:
    """
    #Feature: Evaluation
    #Scenario: Release gate - accuracy floor, zero confidently wrong answers, every fault blocked
    #Complexity: Time O(1)

    Args:
        summary: Run summary.
        gate: Thresholds from config.

    Returns:
        True when the release may proceed.
    """
    try:
        bad_data = summary.buckets.get("bad_data", "0/0").split("/")
        return (summary.in_scope_accuracy >= gate.min_in_scope_accuracy
                and summary.confidently_wrong <= gate.max_confidently_wrong
                and bad_data[0] == bad_data[1])
    except Exception as exc:
        logger.error("gate_passed failed: %s", exc)
        raise


def agent_for(case: EvalCase, config: EvalConfig, agents: dict[str, AgentGraph],
              build: Callable[[WorkspaceConfig], AgentGraph], inject_fault: Callable[[str], Path]) -> AgentGraph:
    """
    #Feature: Evaluation
    #Scenario: Clean agent, or one bound to a warehouse copy with the case's fault (built once per key)
    #Complexity: Time O(warehouse copy) on first use per fault

    Args:
        case: The case.
        config: Eval config.
        agents: Cache of built agents by fault key.
        build: Factory from WorkspaceConfig to agent.
        inject_fault: Creates a faulted warehouse copy and returns its path.

    Returns:
        AgentGraph.
    """
    try:
        key = case.fault or "clean"
        if key not in agents:
            path = inject_fault(case.fault) if case.fault else config.duckdb_path
            agents[key] = build(WorkspaceConfig(
                workspace_id=f"{config.workspace_id}_{key}", dbt_project_dir=config.dbt_project_dir,
                duckdb_path=path, as_of=config.as_of, trace_dir=Path("traces/evals"), llm=llm_settings_from_env()))
        return agents[key]
    except Exception as exc:
        logger.error("agent_for failed for case=%s: %s", case.id, exc)
        raise


def run(cases: list[EvalCase], agent_for_case: AgentForCase, truth: IWarehouseConnector,
        tolerance: float) -> list[EvalResult]:
    """
    #Feature: Evaluation
    #Scenario: Ask every question and grade it
    #Complexity: Time O(cases * (checks + query))

    Args:
        cases: Cases to run.
        agent_for_case: Returns the agent to ask for a case.
        truth: Read-only connector to the clean warehouse.
        tolerance: Relative tolerance.

    Returns:
        Results in case order.
    """
    try:
        results = []
        for case in cases:
            started = time.perf_counter()
            answer = agent_for_case(case).ask(case.question)
            results.append(grade(case, answer, time.perf_counter() - started, truth, tolerance))
            mark = "ok " if results[-1].correct else "FAIL"
            print(f"[{mark}] {case.id} {case.question!r} -> {answer.outcome.value} via {answer.routed_by} "
                  f"({results[-1].detail})")
        return results
    except Exception as exc:
        logger.error("run failed: %s", exc)
        raise


def select_cases(questions_dir: Path, rewordings_file: Path | None, only: str | None) -> list[EvalCase]:
    """
    #Feature: Evaluation
    #Scenario: Base cases, optional rewordings, optional id filter
    #Complexity: Time O(cases)

    Args:
        questions_dir: Directory of questions/*.yaml.
        rewordings_file: rewordings.yaml, or None to skip rewordings.
        only: Comma-separated base case ids, or None for all.

    Returns:
        Cases to run.
    """
    try:
        cases = load_cases(questions_dir)
        if rewordings_file:
            cases += expand_rewordings(cases, rewordings_file)
        if only:
            cases = [c for c in cases if c.id.split(".")[0] in only.split(",")]
        return cases
    except Exception as exc:
        logger.error("select_cases failed: %s", exc)
        raise


def write_results(summary: EvalSummary, results: list[EvalResult], out_dir: Path) -> Path:
    """
    #Feature: Evaluation
    #Scenario: Persist the run as JSON for CI artifacts and the README chart
    #Complexity: Time O(results)

    Args:
        summary: Run summary.
        results: Graded results.
        out_dir: Output directory.

    Returns:
        Path written.
    """
    try:
        out = out_dir / f"{datetime.now():%Y%m%d-%H%M%S}.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        payload = {"summary": summary.model_dump(), "results": [r.model_dump(mode="json") for r in results]}
        out.write_text(json.dumps(payload, indent=2))
        return out
    except Exception as exc:
        logger.error("write_results failed: %s", exc)
        raise
