import json
import logging
from pathlib import Path

import yaml

from truemetric.constants import CHECKS_FILE, SEMANTIC_MANIFEST_PATH
from truemetric.schemas import ChecksConfig
from truemetric.utilities import ManifestIndex

logger = logging.getLogger(__name__)


def load_manifest(project_dir: Path) -> ManifestIndex:
    """
    #Feature: Semantic layer
    #Scenario: Read the compiled semantic manifest from the customer's metric repo
    #Complexity: Time O(manifest size)

    Args:
        project_dir: dbt project directory.

    Returns:
        ManifestIndex.

    Raises:
        ValueError: When the manifest has not been built.
    """
    try:
        path = Path(project_dir) / SEMANTIC_MANIFEST_PATH
        if not path.exists():
            raise ValueError(f"[load_manifest] {path} not found. Invariant violated: the dbt project is parsed. "
                             f"Fix: run `dbt parse` in {project_dir}.")
        return ManifestIndex(json.loads(path.read_text()))
    except Exception as exc:
        logger.error("load_manifest failed: %s", exc)
        raise


def load_checks_config(project_dir: Path) -> ChecksConfig:
    """
    #Feature: Data health checks
    #Scenario: Read truemetric_checks.yml from the customer's metric repo
    #Complexity: Time O(file size)

    Args:
        project_dir: dbt project directory.

    Returns:
        ChecksConfig.
    """
    try:
        return ChecksConfig.model_validate(yaml.safe_load((Path(project_dir) / CHECKS_FILE).read_text()))
    except Exception as exc:
        logger.error("load_checks_config failed: %s", exc)
        raise
