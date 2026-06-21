---
name: test-superset-databases
description: Run read-only connectivity smoke tests against Superset database connections using pytest (not MCP). Use when the user asks to test database connections, verify SQL Lab connectivity, run database smoke tests, or mentions /test-superset-databases without the Superset MCP server.
---

# Test Superset Databases (pytest)

Run the same read-only probes as `/test-superset-databases`, but via **pytest** against databases configured in the Superset metadata DB. Do **not** use the Superset MCP server or browser automation.

If the user typed a filter after the command (e.g. `examples`, `postgresql`, or a database ID), set `SUPERSET_DB_SMOKE_FILTER` to that value before running.

## Prerequisites

1. Activate the project virtual environment (`source venv/bin/activate` or `.venv/bin/activate`).
2. Metadata DB must be initialized (`superset db upgrade` / `superset init`) with at least one database where `expose_in_sqllab` is true.
3. For external databases (PostgreSQL, Presto, etc.), the connection must be reachable from the test environment.

## Run tests

```bash
# All SQL Lab–exposed databases
pytest tests/integration_tests/databases/test_database_smoke.py -v

# Filter by name, backend, or numeric ID
SUPERSET_DB_SMOKE_FILTER=examples pytest tests/integration_tests/databases/test_database_smoke.py -v
SUPERSET_DB_SMOKE_FILTER=postgresql pytest tests/integration_tests/databases/test_database_smoke.py -v
SUPERSET_DB_SMOKE_FILTER=1 pytest tests/integration_tests/databases/test_database_smoke.py -v
```

Use the dev metadata DB when testing a local instance:

```bash
SUPERSET_CONFIG=superset_config pytest tests/integration_tests/databases/test_database_smoke.py -v
```

## Probes (per database)

The test file runs these sequentially (A → B → C → D):

| Probe | SQL / behavior |
|-------|----------------|
| A — connectivity | `SELECT 1 AS ok` |
| B — backend identity | Dialect-specific `version()` (or `SELECT 1` fallback) |
| C — schema visibility | `information_schema` / `sqlite_master` (backend-specific) |
| D — sample data | `COUNT(*)` on first table from probe C |

Only read-only `SELECT` queries run. Databases with `expose_in_sqllab=false` are skipped unless the filter explicitly matches them by name or ID.

## Agent workflow

1. Confirm the user wants pytest (not MCP). If they asked for `/test-superset-databases` and MCP is unavailable, use this skill.
2. Apply any filter from the user's message via `SUPERSET_DB_SMOKE_FILTER`.
3. Run pytest with `-v` and capture output.
4. Return a report in this format:

```markdown
## Superset database smoke test

**Source:** pytest (`tests/integration_tests/databases/test_database_smoke.py`)
**Filter:** <filter or "all">
**Tested at:** <timestamp>

| Database | ID | Backend | SQL Lab | Connectivity | Version probe | Schema probe | Sample data | Notes |
|----------|----|---------|---------|--------------|---------------|--------------|-------------|-------|

### Failures (if any)

Database name, probe name, error message, suggested next step.

### Summary

- X/Y databases passed all probes
- Backends needing custom probe SQL (if any)
```

## Error handling

- **OAuth / auth redirect:** Report clearly; user must complete OAuth in Superset UI first.
- **Empty database list:** Suggest Superset → Settings → Database Connections.
- **Connection refused / timeout:** Check database host, credentials, and network from the test environment.
- **Probe failures on `version()`:** Direct engine access via `Database.get_df()` bypasses SQL Lab validators; failures indicate real connectivity or permission issues, not MCP validation rules.

## Optional follow-ups (only if the user asks)

- Re-run with a narrower `SUPERSET_DB_SMOKE_FILTER`
- Run MCP `/test-superset-databases` to compare SQL Lab validation behavior
- `pytest tests/integration_tests/sqllab_tests.py` for broader SQL Lab coverage
