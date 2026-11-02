"""Copy the warehouse and plant one data fault in the marts, for the bad-data eval bucket.

The copy keeps the file name warehouse.duckdb so compiled MetricFlow SQL still resolves.
"""

import logging
import shutil
from collections.abc import Callable
from pathlib import Path

import duckdb

logger = logging.getLogger("inject_fault")

Connect = Callable[[str], duckdb.DuckDBPyConnection]

FAULTS = {
    "late_partition": [
        "delete from analytics.fct_order_items where created_at >= date '2026-10-31'",
        "delete from analytics.fct_orders where created_at >= date '2026-10-31'",
    ],
    "duplicated_batch": [
        "insert into analytics.fct_order_items select * from analytics.fct_order_items "
        "where cast(created_at as date) = date '2026-10-30'",
    ],
    "renamed_column": [
        "alter table analytics.fct_order_items rename column sale_price to sale_price_usd",
    ],
    "null_sale_price": [
        "update analytics.fct_order_items set sale_price = null where created_at >= date '2026-10-28'",
    ],
    "currency_unit_change": [
        "update analytics.fct_order_items set sale_price = sale_price * 100, cost = cost * 100, "
        "gross_revenue_amount = gross_revenue_amount * 100, returned_revenue_amount = returned_revenue_amount * 100, "
        "margin_amount = margin_amount * 100 where created_at >= date '2026-10-25'",
    ],
}


def inject(source: Path, out_dir: Path, fault: str, connect: Connect) -> Path:
    """
    #Feature: Fault injection
    #Scenario: Copy the warehouse into out_dir/<fault>/ and apply one fault
    #Complexity: Time O(warehouse size)

    Args:
        source: Clean warehouse DuckDB file.
        out_dir: Directory for faulted copies.
        fault: One of FAULTS.
        connect: Opens a read-write connection to a DuckDB file.

    Returns:
        Path of the faulted warehouse.

    Raises:
        ValueError: When fault is unknown or source is missing.
    """
    try:
        if fault not in FAULTS:
            raise ValueError(f"[inject] Unknown fault {fault!r}. Fix: use one of {', '.join(FAULTS)}.")
        if not source.exists():
            raise ValueError(f"[inject] {source} not found. Fix: generate data and run dbt build first.")
        target = out_dir / fault / source.name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        with connect(str(target)) as con:
            for statement in FAULTS[fault]:
                con.execute(statement)
        logger.info("injected fault=%s into %s", fault, target)
        return target
    except Exception as exc:
        logger.error("inject failed for fault=%s: %s", fault, exc)
        raise
