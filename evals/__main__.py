"""Eval CLI.

python -m evals run [--rewordings] [--only s01,x01]   run the benchmark; exits 1 when the release gate fails
python -m evals faults all|<fault>                     create faulted warehouse copies
"""

import argparse
import logging
import sys
from pathlib import Path

import duckdb
import yaml

from evals.faults import FAULTS, inject
from evals.run_evals import (
    RAW_SCHEMA,
    TRUTH_MAX_ROWS,
    EvalConfig,
    agent_for,
    gate_passed,
    run,
    select_cases,
    summarize,
    write_results,
)
from truemetric.agent import AgentGraph
from truemetric.composition import build_services
from truemetric.connectors import DuckDBConnector

logger = logging.getLogger("evals")


def parse_args() -> argparse.Namespace:
    """
    #Feature: Evaluation
    #Scenario: Command-line options for the run and faults subcommands
    #Complexity: Time O(1)

    Returns:
        Parsed arguments.
    """
    try:
        parser = argparse.ArgumentParser(description=__doc__)
        commands = parser.add_subparsers(dest="command", required=True)
        runner = commands.add_parser("run", help="Run the benchmark and the release gate")
        runner.add_argument("--config", type=Path, default=Path("evals/config.yml"))
        runner.add_argument("--only", help="Comma-separated case ids")
        runner.add_argument("--rewordings", action="store_true", help="Also run evals/rewordings.yaml")
        faults = commands.add_parser("faults", help="Create faulted warehouse copies")
        faults.add_argument("fault", choices=[*FAULTS, "all"])
        faults.add_argument("--config", type=Path, default=Path("evals/config.yml"))
        return parser.parse_args()
    except Exception as exc:
        logger.error("parse_args failed: %s", exc)
        raise


def run_command(args: argparse.Namespace, config: EvalConfig) -> bool:
    """
    #Feature: Evaluation
    #Scenario: Composition root for an eval run
    #Complexity: Time O(cases * (checks + query))

    Args:
        args: Parsed arguments.
        config: Eval config.

    Returns:
        True when the release gate passed.
    """
    try:
        truth = DuckDBConnector(config.duckdb_path, RAW_SCHEMA, TRUTH_MAX_ROWS, f"{config.workspace_id}_truth")
        agents: dict[str, AgentGraph] = {}
        build = lambda workspace: build_services(workspace).agent  # noqa: E731
        inject_fault = lambda fault: inject(config.duckdb_path, config.fault_dir, fault, duckdb.connect)  # noqa: E731
        cases = select_cases(args.config.parent / "questions",
                             args.config.parent / "rewordings.yaml" if args.rewordings else None, args.only)
        results = run(cases, lambda case: agent_for(case, config, agents, build, inject_fault), truth,
                      config.tolerance)
        summary = summarize(results)
        out = write_results(summary, results, Path("evals/results"))
        passed = gate_passed(summary, config.gate)
        print(summary.model_dump_json(indent=2), f"\nGate {'PASSED' if passed else 'FAILED'}. Results: {out}")
        return passed
    except Exception as exc:
        logger.error("run_command failed: %s", exc)
        raise


def main() -> None:
    """
    #Feature: Evaluation
    #Scenario: CLI entry point; exits 1 when the gate fails
    #Complexity: Time O(cases * (checks + query))
    """
    try:
        args = parse_args()
        config = EvalConfig.model_validate(yaml.safe_load(args.config.read_text()))
        if args.command == "faults":
            logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
            for fault in FAULTS if args.fault == "all" else [args.fault]:
                inject(config.duckdb_path, config.fault_dir, fault, duckdb.connect)
            return
        logging.basicConfig(level=logging.ERROR)
        logging.getLogger("truemetric.agent.parsers.llm_parser").setLevel(logging.WARNING)
        sys.exit(0 if run_command(args, config) else 1)
    except Exception as exc:
        logger.error("main failed: %s", exc)
        raise


if __name__ == "__main__":
    main()
