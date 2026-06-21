# Test Superset Databases via MCP

Run read-only connectivity and query smoke tests against Superset database connections using the **Superset MCP** server. Do not use browser automation, shell SQL clients, or generated Python scripts — call MCP tools directly.

If the user typed text after this command (e.g. `/test-superset-databases examples`), treat it as a filter: match database names, IDs, or backends; otherwise test all accessible databases.

## Prerequisites

1. Confirm the Superset MCP server is connected. If `health_check` or `call_tool` is unavailable, stop and tell the user to enable the Superset MCP integration.
2. Confirm the current user has SQL Lab access (`execute_sql_query`). If `execute_sql` is missing from the tool list, stop and explain that SQL execution permission is required.

## Workflow

### 1. Instance sanity check

Call `health_check` (no parameters).

Then call `get_instance_info` to capture the instance name, current user, and feature availability.

### 2. Discover databases

Call `list_databases` with `request={}` (or with filters if the user named specific databases).

For each database to test:

- Call `get_database_info` with `request={"identifier": <id>}`.
- Record: `id`, `database_name`, `backend`, `expose_in_sqllab`, `allow_dml`.

Skip databases where `expose_in_sqllab` is false unless the user explicitly asked to test them.

### 3. Run test queries (read-only)

For **each** database, run these probes via `execute_sql`. Always pass `request={"database_id": <id>, "sql": "...", "limit": 10}` unless a query already includes `LIMIT`.

Use `limit` generously (10–100) to keep responses small.

#### Probe A — connectivity (all backends)

```sql
SELECT 1 AS ok
```

Pass if `success` is true and `rows` contains `ok = 1`.

#### Probe B — backend identity (all backends)

Pick the dialect-appropriate query:

| Backend | SQL |
|---------|-----|
| postgresql | `SELECT version() AS version` |
| mysql / mariadb | `SELECT VERSION() AS version` |
| sqlite | `SELECT sqlite_version() AS version` |
| presto / trino | `SELECT version() AS version` |
| bigquery | `SELECT 1 AS ok` (skip version if unsupported) |
| other | `SELECT 1 AS ok` |

#### Probe C — schema visibility (all backends)

| Backend | SQL |
|---------|-----|
| postgresql | `SELECT table_schema, table_name FROM information_schema.tables WHERE table_schema NOT IN ('pg_catalog', 'information_schema') ORDER BY 1, 2 LIMIT 10` |
| mysql / mariadb | `SELECT table_schema, table_name FROM information_schema.tables WHERE table_schema NOT IN ('mysql', 'information_schema', 'performance_schema', 'sys') ORDER BY 1, 2 LIMIT 10` |
| sqlite | `SELECT name AS table_name FROM sqlite_master WHERE type = 'table' ORDER BY 1 LIMIT 10` |
| other | Skip and note "schema probe not defined for backend" |

#### Probe D — sample data (optional, when Probe C returns tables)

Choose the first table from Probe C results. Run a row-count or sample query:

```sql
SELECT COUNT(*) AS row_count FROM "<schema>"."<table>"
```

For backends without schemas, use `FROM <table>`. Quote identifiers that contain spaces or special characters. If the table is empty or inaccessible, record the error and continue.

**Do not run** `INSERT`, `UPDATE`, `DELETE`, `DROP`, `CREATE`, `ALTER`, or any DDL/DML. If a probe fails because `allow_dml` is false, that is expected — only report it if a SELECT failed unexpectedly.

### 4. Parallelize safely

You may call `execute_sql` for different databases in parallel. Run probes A → B → C → D sequentially per database so later probes can use earlier results.

## Output format

Return a concise report:

```markdown
## Superset database smoke test

**Instance:** <name from get_instance_info>
**User:** <username>
**Tested at:** <timestamp>

| Database | ID | Backend | SQL Lab | Connectivity | Version probe | Schema probe | Sample data | Notes |
|----------|----|---------|---------|--------------|---------------|--------------|-------------|-------|
| examples | 1  | postgresql | yes | pass | pass | 20 tables | pass (birth_names: N rows) | |

### Failures (if any)

For each failure: database name, probe name, error message, and suggested next step (permissions, connection config, OAuth redirect, etc.).

### Summary

- X/Y databases passed all probes
- List any backends that need custom probe SQL added
```

Keep raw result rows out of the report unless the user asked for sample data. Include execution times only when a probe is suspiciously slow (>5s).

## Error handling

- **OAuth / auth redirect errors:** Report clearly; do not retry in a loop. Suggest the user complete OAuth in Superset UI first.
- **Permission denied:** Note which database failed RBAC and continue with others.
- **Empty database list:** Say no connections were found and suggest checking Superset → Settings → Database Connections.
- **Tool errors:** Call `generate_bug_report` only if the MCP itself appears broken, not for ordinary SQL errors.

## Optional follow-ups (only if the user asks)

- `list_datasets` filtered by `database_id` to cross-check datasets against live tables
- `query_dataset` on an example dataset tied to the database
- `open_sql_lab_with_context` with a passing probe query for manual exploration
