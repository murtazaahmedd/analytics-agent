import logging
import os
import tempfile
from functools import lru_cache
from pathlib import Path

from metricflow.engine.metricflow_engine import AbstractMetricFlowEngine

from truemetric.constants import ENV_DBT_DUCKDB_PATH

logger = logging.getLogger(__name__)


@lru_cache(maxsize=16)
def load_engine(project_dir: str, duckdb_name: str) -> AbstractMetricFlowEngine:
    """
    #Feature: Semantic layer
    #Scenario: Build a MetricFlow engine once per dbt project (startup takes seconds)
    #Complexity: Time O(project size) on first call, O(1) after

    The engine only compiles SQL; its dbt adapter opens a read-write connection, so it gets an empty
    placeholder file with the same name. The file name sets the database name in compiled SQL, so
    warehouse copies (fault injection) must keep the same file name.

    Args:
        project_dir: Absolute dbt project directory containing profiles.yml.
        duckdb_name: Warehouse DuckDB file name.

    Returns:
        MetricFlow engine.
    """
    try:
        from dbt_metricflow.cli.cli_configuration import CLIConfiguration

        placeholder = Path(tempfile.mkdtemp(prefix="truemetric-mf-")) / duckdb_name
        os.environ[ENV_DBT_DUCKDB_PATH] = str(placeholder)
        cli = CLIConfiguration()
        cli.setup(dbt_profiles_path=Path(project_dir), dbt_project_path=Path(project_dir), configure_file_logging=False)
        return cli.mf
    except Exception as exc:
        logger.error("load_engine failed for project_dir=%s: %s", project_dir, exc)
        raise
