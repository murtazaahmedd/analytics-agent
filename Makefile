PY ?= python
DBT_DIR := demo_workspaces/thelook
DBT := cd $(DBT_DIR) && TRUEMETRIC_DUCKDB_PATH=../../data/warehouse.duckdb dbt

.PHONY: install data dbt faults test evals ask mcp-semantic mcp-warehouse mcp-checks

install:
	$(PY) -m pip install -e ".[dev]"

data:
	$(PY) scripts/generate_thelook.py
	$(MAKE) dbt

dbt:
	$(DBT) build --profiles-dir .

faults:
	$(PY) -m evals faults all

test:
	$(PY) -m pytest -q

evals:
	$(PY) -m evals run --rewordings

ask:
	$(PY) -m truemetric "$(Q)"

MCP_ENV := TRUEMETRIC_WORKSPACE_ID=demo TRUEMETRIC_DBT_PROJECT_DIR=$(DBT_DIR) \
	TRUEMETRIC_WAREHOUSE_PATH=data/warehouse.duckdb TRUEMETRIC_AS_OF=2026-11-01T00:00:00

mcp-semantic:
	$(MCP_ENV) $(PY) -m truemetric.mcp_servers.semantic_layer

mcp-warehouse:
	$(MCP_ENV) $(PY) -m truemetric.mcp_servers.warehouse

mcp-checks:
	$(MCP_ENV) $(PY) -m truemetric.mcp_servers.checks
