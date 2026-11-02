import logging
import time as clock
from collections.abc import Callable
from datetime import datetime, timedelta

from truemetric.interfaces import IDataChecks, IWarehouseConnector
from truemetric.schemas import CheckResult, CheckRun, ChecksConfig, TableCheckConfig
from truemetric.constants import DISTRIBUTION_BASELINE_DAYS, DISTRIBUTION_RECENT_DAYS, VOLUME_BASELINE_DAYS
from truemetric.utilities import quote_identifier, require

logger = logging.getLogger(__name__)


def ratio_result(table: str, check: str, ratio: float | None, low: float, high: float, what: str) -> CheckResult:
    """
    #Feature: Data health checks
    #Scenario: Turn a measured ratio into a pass/fail result
    #Complexity: Time O(1)

    Args:
        table: Table name.
        check: Check name.
        ratio: Measured ratio, None when the baseline is empty.
        low: Minimum allowed ratio.
        high: Maximum allowed ratio.
        what: Human description of the ratio.

    Returns:
        CheckResult.
    """
    try:
        if ratio is None:
            return CheckResult(table=table, check=check, passed=False, detail=f"No baseline data for {what}.")
        passed = low <= ratio <= high
        return CheckResult(table=table, check=check, passed=passed,
                           detail=f"{what} is {ratio:.2f}x the baseline (allowed {low}-{high}x).")
    except Exception as exc:
        logger.error("ratio_result failed for table=%s: %s", table, exc)
        raise


class WarehouseDataChecks(IDataChecks):
    """
    #Feature: Data health checks
    #Scenario: SQL checks configured in truemetric_checks.yml, cached per table for a short TTL
    #Complexity: Time O(tables * checks)
    """

    def __init__(self, connector: IWarehouseConnector, config: ChecksConfig, now: Callable[[], datetime],
                 workspace_id: str, cache_ttl_seconds: float = 300.0) -> None:
        """
        #Feature: Data health checks
        #Scenario: Bind checks to a workspace warehouse and clock
        #Complexity: Time O(1)

        Args:
            connector: Read-only warehouse connector.
            config: Parsed truemetric_checks.yml.
            now: Clock returning the workspace "now".
            workspace_id: Tenant id for logs.
            cache_ttl_seconds: How long a table's results are reused.
        """
        try:
            self._connector, self._config, self._now = connector, config, now
            self._workspace_id, self._ttl = workspace_id, cache_ttl_seconds
            self._cache: dict[str, tuple[float, list[CheckResult]]] = {}
            self._last_run: CheckRun | None = None
        except Exception as exc:
            logger.error("WarehouseDataChecks init failed: %s", exc, extra={"tenant_id": workspace_id})
            raise

    def _scalar(self, sql: str, params: list | None = None) -> object:
        """
        #Feature: Data health checks
        #Scenario: Run a single-value query
        #Complexity: Time O(query)

        Args:
            sql: SELECT returning one row and one column.
            params: Bind parameters.

        Returns:
            The value.
        """
        try:
            return self._connector.execute(sql, params)[1][0][0]
        except Exception as exc:
            logger.error("_scalar failed: %s", exc, extra={"tenant_id": self._workspace_id})
            raise

    def _schema(self, table: str, rule: TableCheckConfig) -> CheckResult:
        """
        #Feature: Data health checks
        #Scenario: Table exists and has every required column (catches renamed columns)
        #Complexity: Time O(columns)

        Args:
            table: Table name.
            rule: Table checks.

        Returns:
            CheckResult.
        """
        try:
            actual = self._connector.table_columns(table)
            if not actual:
                return CheckResult(table=table, check="schema", passed=False, detail="Table is missing.")
            missing = [c for c in rule.required_columns if c not in actual]
            detail = f"Missing columns: {', '.join(missing)}." if missing else "All required columns present."
            return CheckResult(table=table, check="schema", passed=not missing, detail=detail)
        except Exception as exc:
            logger.error("_schema failed for table=%s: %s", table, exc, extra={"tenant_id": self._workspace_id})
            raise

    def _freshness(self, table: str, rule: TableCheckConfig) -> CheckResult:
        """
        #Feature: Data health checks
        #Scenario: Newest row is within freshness_hours of now (catches late partitions)
        #Complexity: Time O(rows)

        Args:
            table: Table name.
            rule: Table checks.

        Returns:
            CheckResult.
        """
        try:
            newest = self._scalar(f"select max({quote_identifier(rule.timestamp_column)}) "
                                  f"from {self._connector.qualify(table)}")
            if newest is None:
                return CheckResult(table=table, check="freshness", passed=False, detail="Table has no rows.")
            lag = (self._now() - newest).total_seconds() / 3600
            return CheckResult(table=table, check="freshness", passed=lag <= rule.freshness_hours,
                               detail=f"Newest row is {lag:.1f}h old (allowed {rule.freshness_hours}h); "
                                      f"latest {newest:%Y-%m-%d %H:%M}.")
        except Exception as exc:
            logger.error("_freshness failed for table=%s: %s", table, exc, extra={"tenant_id": self._workspace_id})
            raise

    def _volume(self, table: str, rule: TableCheckConfig) -> CheckResult:
        """
        #Feature: Data health checks
        #Scenario: Last complete day's rows vs. trailing 7-day average (catches drops and spikes)
        #Complexity: Time O(rows)

        Args:
            table: Table name.
            rule: Table checks.

        Returns:
            CheckResult.
        """
        try:
            day = self._now().date() - timedelta(days=1)
            ts = f"cast({quote_identifier(rule.timestamp_column)} as date)"
            sql = (f"select count(*) filter (where {ts} = ?) * 1.0, "
                   f"count(*) filter (where {ts} between ? and ?) / {VOLUME_BASELINE_DAYS}.0 "
                   f"from {self._connector.qualify(table)}")
            params = [day, day - timedelta(days=VOLUME_BASELINE_DAYS), day - timedelta(days=1)]
            latest, baseline = self._connector.execute(sql, params)[1][0]
            ratio = float(latest) / float(baseline) if baseline else None
            return ratio_result(table, "volume", ratio, rule.volume.min_ratio, rule.volume.max_ratio,
                                f"Row count on {day}")
        except Exception as exc:
            logger.error("_volume failed for table=%s: %s", table, exc, extra={"tenant_id": self._workspace_id})
            raise

    def _unique(self, table: str, rule: TableCheckConfig) -> CheckResult:
        """
        #Feature: Data health checks
        #Scenario: Primary key is unique (catches duplicated batches)
        #Complexity: Time O(rows)

        Args:
            table: Table name.
            rule: Table checks.

        Returns:
            CheckResult.
        """
        try:
            key = quote_identifier(rule.unique_key)
            dupes = self._scalar(f"select count(*) - count(distinct {key}) from {self._connector.qualify(table)}")
            return CheckResult(table=table, check="unique", passed=dupes == 0,
                               detail=f"{dupes} duplicate {rule.unique_key} values.")
        except Exception as exc:
            logger.error("_unique failed for table=%s: %s", table, exc, extra={"tenant_id": self._workspace_id})
            raise

    def _not_null(self, table: str, rule: TableCheckConfig) -> CheckResult:
        """
        #Feature: Data health checks
        #Scenario: Required columns contain no nulls
        #Complexity: Time O(rows * columns)

        Args:
            table: Table name.
            rule: Table checks.

        Returns:
            CheckResult.
        """
        try:
            counts = ", ".join(f"count(*) - count({quote_identifier(c)})" for c in rule.not_null_columns)
            _, rows = self._connector.execute(f"select {counts} from {self._connector.qualify(table)}")
            bad = {c: n for c, n in zip(rule.not_null_columns, rows[0]) if n}
            detail = ", ".join(f"{n} nulls in {c}" for c, n in bad.items()) or "No nulls in required columns"
            return CheckResult(table=table, check="not_null", passed=not bad, detail=detail + ".")
        except Exception as exc:
            logger.error("_not_null failed for table=%s: %s", table, exc, extra={"tenant_id": self._workspace_id})
            raise

    def _distribution(self, table: str, rule: TableCheckConfig) -> CheckResult:
        """
        #Feature: Data health checks
        #Scenario: Recent 7-day mean vs. prior 28-day mean (catches unit changes)
        #Complexity: Time O(rows)

        Args:
            table: Table name.
            rule: Table checks.

        Returns:
            CheckResult.
        """
        try:
            day = self._now().date() - timedelta(days=1)
            ts = f"cast({quote_identifier(rule.timestamp_column)} as date)"
            col = quote_identifier(rule.distribution.column)
            sql = (f"select avg({col}) filter (where {ts} between ? and ?), "
                   f"avg({col}) filter (where {ts} between ? and ?) from {self._connector.qualify(table)}")
            recent_start = day - timedelta(days=DISTRIBUTION_RECENT_DAYS - 1)
            params = [recent_start, day, recent_start - timedelta(days=DISTRIBUTION_BASELINE_DAYS),
                      recent_start - timedelta(days=1)]
            recent, baseline = self._connector.execute(sql, params)[1][0]
            ratio = float(recent) / float(baseline) if recent is not None and baseline else None
            return ratio_result(table, "distribution", ratio, rule.distribution.min_ratio,
                                rule.distribution.max_ratio, f"Mean {rule.distribution.column} over the last 7 days")
        except Exception as exc:
            logger.error("_distribution failed for table=%s: %s", table, exc, extra={"tenant_id": self._workspace_id})
            raise

    def _planned(self, rule: TableCheckConfig) -> list[Callable[[str, TableCheckConfig], CheckResult]]:
        """
        #Feature: Data health checks
        #Scenario: Checks that apply to a table, given its configuration
        #Complexity: Time O(1)

        Args:
            rule: Table checks.

        Returns:
            Check functions to run after the schema check passes.
        """
        try:
            planned = []
            if rule.timestamp_column and rule.freshness_hours:
                planned.append(self._freshness)
            if rule.timestamp_column and rule.volume:
                planned.append(self._volume)
            if rule.unique_key:
                planned.append(self._unique)
            if rule.not_null_columns:
                planned.append(self._not_null)
            if rule.timestamp_column and rule.distribution:
                planned.append(self._distribution)
            return planned
        except Exception as exc:
            logger.error("_planned failed: %s", exc, extra={"tenant_id": self._workspace_id})
            raise

    def _check_table(self, table: str) -> list[CheckResult]:
        """
        #Feature: Data health checks
        #Scenario: Run all checks for one table; any error fails closed
        #Complexity: Time O(checks)

        Args:
            table: Table name.

        Returns:
            Results for the table.
        """
        try:
            rule = self._config.tables.get(table)
            if rule is None:
                return [CheckResult(table=table, check="configured", passed=False,
                                    detail="No checks configured; refusing to trust this table.")]
            schema = self._schema(table, rule)
            if not schema.passed:
                return [schema]
            results = [schema]
            for check in self._planned(rule):
                try:
                    results.append(check(table, rule))
                except Exception as check_exc:
                    results.append(CheckResult(table=table, check=check.__name__.strip("_"), passed=False,
                                               detail=f"Check errored: {check_exc}"))
            return results
        except Exception as exc:
            logger.error("_check_table failed for table=%s: %s", table, exc, extra={"tenant_id": self._workspace_id})
            raise

    def run_checks(self, tables: list[str]) -> CheckRun:
        """
        #Feature: Data health checks
        #Scenario: Run every configured check on the given marts, reusing results younger than the cache TTL
        #Complexity: Time O(tables * checks)

        Args:
            tables: Mart table names; unconfigured tables fail closed.

        Returns:
            CheckRun with one result per check.

        Raises:
            ValueError: When tables is None.
        """
        try:
            require("WarehouseDataChecks.run_checks", tables=(tables, list))
            results = []
            for table in tables:
                cached = self._cache.get(table)
                if cached is None or clock.monotonic() - cached[0] > self._ttl:
                    cached = (clock.monotonic(), self._check_table(table))
                    self._cache[table] = cached
                results.extend(cached[1])
            run = CheckRun(ran_at=self._now(), results=results)
            self._last_run = run
            logger.info("run_checks tables=%s passed=%s", tables, run.passed, extra={"tenant_id": self._workspace_id})
            return run
        except Exception as exc:
            logger.error("run_checks failed: %s", exc, extra={"tenant_id": self._workspace_id})
            raise

    def get_last_run(self) -> CheckRun | None:
        """
        #Feature: Data health checks
        #Scenario: Most recent run, for the data health page
        #Complexity: Time O(1)

        Returns:
            The last run, or None if no checks have run.
        """
        try:
            return self._last_run
        except Exception as exc:
            logger.error("get_last_run failed: %s", exc, extra={"tenant_id": self._workspace_id})
            raise
