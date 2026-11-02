# TrueMetric (analytics-agent)

An AI data agent that answers business questions **only through an approved metric layer**, checks the
data before answering, and refuses rather than guesses.

Every question takes one fixed path:

```text
question -> Router -> unclear?        -> ask one clarifying question
                   -> no metric?      -> refuse + log a metric gap
                   -> why-question?   -> (root-cause step, planned)
                   -> Data guard -> checks fail? -> block, name the failed check
                                 -> Answerer (MetricFlow -> read-only SQL) -> number + definition + SQL + trace
```

## Status

Phase 1 (weeks 1-3, Gate A) is done and runs locally on DuckDB:

| Piece | Where |
| --- | --- |
| thelook-shaped synthetic dataset (deterministic, with planted anomalies) | `scripts/generate_thelook.py` |
| dbt staging / intermediate / marts + 15 starter metrics in MetricFlow | `demo_workspaces/thelook/` |
| Data checks: freshness, volume, schema, not-null, uniqueness, distribution | `truemetric/tools/data_checks.py`, `truemetric_checks.yml` |
| 5 fault-injection scripts | `evals/faults.py` |
| Semantic layer, warehouse and checks tools + MCP servers | `truemetric/tools/`, `truemetric/mcp_servers/` |
| Agent state machine (router, data guard, answerer) | `truemetric/agent/` |
| LLM router via LiteLLM, with a deterministic rule-based fallback | `truemetric/agent/parsers/` |
| 40-question eval suite + 81 rewordings + CI release gate | `evals/`, `.github/workflows/ci.yml` |

Latest eval run (rule-based router, no LLM): 40/40 on the base set, 58/81 on rewordings, **0 confidently wrong
across all 121**, 5/5 faults blocked, p95 latency 0.3 s. Every rewording miss is a refusal or a clarifying
question, not a wrong number. The LLM router is meant to close that coverage gap; it has not yet been evaluated
end to end (see below).

## Quick start

```bash
conda env create -f environment.yml
conda activate analytics
make data          # generate data/warehouse.duckdb and run dbt build
make test          # unit + integration tests
make evals         # benchmark + release gate
make ask Q="AOV by country, last quarter, top 5"
```

The demo workspace pins "today" to 2026-11-01 so relative dates ("last week") are reproducible.

### Use an LLM router

```bash
export TRUEMETRIC_LLM_MODEL=gemini/gemini-3.5-flash   # any LiteLLM model id
export TRUEMETRIC_LLM_FALLBACKS=gemini/gemini-2.5-flash  # optional, comma-separated
export GEMINI_API_KEY=...
```

Set `TRUEMETRIC_LLM_REASONING_EFFORT=disable` for Gemini Flash (about 1 s per call instead of 8-10 s).
The Gemini free tier allows only 20 requests per model per day, which is too few for an eval run (121 calls).
Each answer records `routed_by` (`llm` or `rules`), and the eval summary reports `routed_by_llm`, so a run that
silently fell back to rules is visible.

Without `TRUEMETRIC_LLM_MODEL` the rule-based parser is used. The LLM only routes; it never produces numbers,
and any metric it names that is not in the catalog is refused.

### MCP servers

```bash
make mcp-semantic    # list_metrics, describe_metric, query_metric
make mcp-warehouse   # profile_table, check_freshness, run_sql_readonly
make mcp-checks      # run_checks, get_last_run
```

All three use stdio and read the workspace from `TRUEMETRIC_WORKSPACE_ID`, `TRUEMETRIC_DBT_PROJECT_DIR`,
`TRUEMETRIC_WAREHOUSE_PATH` and `TRUEMETRIC_AS_OF`.

## Guardrails

- Numbers come only from `ISemanticLayer.query_metric` (MetricFlow-compiled SQL).
- Warehouse connections are read-only, and any SQL that is not a single SELECT/WITH is rejected.
- The data guard runs on every mart a query touches, including dimension tables, and fails closed:
  unconfigured tables and erroring checks both block the answer.
- Month-grain metrics (repeat purchase rate) are never aggregated across months.
- Every step is written to `traces/<workspace_id>.jsonl` (stand-in for Langfuse).

## Roadmap

- **Phase 2 (weeks 4-6, Gate B):** FastAPI control plane (workspaces, users, roles, Postgres UDFs, RLS),
  connect-a-warehouse flow, onboarding agent, Next.js ask screen, Slack app, second demo schema.
- **Phase 3 (weeks 7-9, Gate C):** Pub/Sub workers, isolation tests, gap drafter that opens dbt PRs,
  cost and byte caps, full 80-question eval, Terraform.
- **Phase 4 (weeks 10-12):** root-cause step, data health page, audit log, pilots.
