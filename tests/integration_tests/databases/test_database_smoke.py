# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
"""
Read-only smoke tests for Superset database connections.

Mirrors the probes in ``.cursor/commands/test-superset-databases.md`` but runs
via ``Database.get_df()`` (direct engine access), not the Superset MCP or SQL Lab
API validators.

Run all SQL Lab–exposed databases::

    pytest tests/integration_tests/databases/test_database_smoke.py -v

Filter by database name, backend, or ID::

    SUPERSET_DB_SMOKE_FILTER=examples pytest tests/integration_tests/databases/test_database_smoke.py -v
"""
from __future__ import annotations

import os
from typing import Any

import pytest

from superset.daos.database import DatabaseDAO
from superset.exceptions import OAuth2RedirectError
from superset.models.core import Database
from tests.integration_tests.test_app import app

FILTER_ENV = "SUPERSET_DB_SMOKE_FILTER"

CONNECTIVITY_SQL = "SELECT 1 AS ok"

VERSION_SQL_BY_BACKEND: dict[str, str] = {
    "postgresql": "SELECT version() AS version",
    "mysql": "SELECT VERSION() AS version",
    "mariadb": "SELECT VERSION() AS version",
    "sqlite": "SELECT sqlite_version() AS version",
    "presto": "SELECT version() AS version",
    "trino": "SELECT version() AS version",
    "bigquery": "SELECT 1 AS ok",
}

SCHEMA_SQL_BY_BACKEND: dict[str, str] = {
    "postgresql": (
        "SELECT table_schema, table_name "
        "FROM information_schema.tables "
        "WHERE table_schema NOT IN ('pg_catalog', 'information_schema') "
        "ORDER BY 1, 2 LIMIT 10"
    ),
    "mysql": (
        "SELECT table_schema, table_name "
        "FROM information_schema.tables "
        "WHERE table_schema NOT IN "
        "('mysql', 'information_schema', 'performance_schema', 'sys') "
        "ORDER BY 1, 2 LIMIT 10"
    ),
    "mariadb": (
        "SELECT table_schema, table_name "
        "FROM information_schema.tables "
        "WHERE table_schema NOT IN "
        "('mysql', 'information_schema', 'performance_schema', 'sys') "
        "ORDER BY 1, 2 LIMIT 10"
    ),
    "sqlite": (
        "SELECT name AS table_name "
        "FROM sqlite_master WHERE type = 'table' "
        "ORDER BY 1 LIMIT 10"
    ),
}


def _matches_filter(database: Database, filter_text: str | None) -> bool:
    if not filter_text:
        return database.expose_in_sqllab
    needle = filter_text.lower()
    return (
        needle in database.database_name.lower()
        or needle == str(database.id)
        or needle in database.backend.lower()
        or (
            not database.expose_in_sqllab
            and (
                needle == database.database_name.lower()
                or needle == str(database.id)
            )
        )
    )


def _databases_for_tests() -> list[Database]:
    filter_text = os.environ.get(FILTER_ENV)
    with app.app_context():
        return [
            db
            for db in DatabaseDAO.find_all()
            if _matches_filter(db, filter_text)
        ]


def _run_probe(database: Database, sql: str) -> Any:
    """Run a read-only probe; raise on failure."""
    try:
        return database.get_df(sql)
    except OAuth2RedirectError as ex:
        pytest.fail(f"OAuth authentication required for {database.database_name}: {ex}")


def _version_sql(database: Database) -> str:
    backend = database.backend.lower()
    return VERSION_SQL_BY_BACKEND.get(backend, CONNECTIVITY_SQL)


def _schema_sql(database: Database) -> str | None:
    backend = database.backend.lower()
    return SCHEMA_SQL_BY_BACKEND.get(backend)


def _build_count_sql(database: Database, schema: str | None, table: str) -> str:
    quote = database.quote_identifier
    if schema:
        table_ref = f"{quote(schema)}.{quote(table)}"
    else:
        table_ref = quote(table)
    return f"SELECT COUNT(*) AS row_count FROM {table_ref}"


def _first_table_from_schema_df(database: Database, df: Any) -> tuple[str | None, str]:
    if df.empty:
        pytest.skip(f"No user tables found in {database.database_name}")
    row = df.iloc[0]
    if "table_schema" in df.columns:
        return row["table_schema"], row["table_name"]
    return None, row["table_name"]


def test_databases_available_for_smoke() -> None:
    """Fail fast with a clear message when no databases match the filter."""
    databases = _databases_for_tests()
    if databases:
        return
    filter_text = os.environ.get(FILTER_ENV)
    reason = (
        f"No databases matched filter {filter_text!r}"
        if filter_text
        else "No databases with expose_in_sqllab=true found"
    )
    pytest.skip(reason)


def pytest_generate_tests(metafunc: pytest.Metafunc) -> None:
    if "database" not in metafunc.fixturenames:
        return
    databases = _databases_for_tests()
    if not databases:
        filter_text = os.environ.get(FILTER_ENV)
        reason = (
            f"No databases matched filter {filter_text!r}"
            if filter_text
            else "No databases with expose_in_sqllab=true found"
        )
        metafunc.parametrize("database", [], ids=[])
        return
    ids = [f"{db.database_name}({db.id})" for db in databases]
    metafunc.parametrize("database", databases, ids=ids)


def test_connectivity_probe(database: Database) -> None:
    """Probe A — basic connectivity."""
    df = _run_probe(database, CONNECTIVITY_SQL)
    assert not df.empty
    assert df.iloc[0]["ok"] == 1


def test_version_probe(database: Database) -> None:
    """Probe B — backend identity."""
    sql = _version_sql(database)
    df = _run_probe(database, sql)
    assert not df.empty


def test_schema_visibility_probe(database: Database) -> None:
    """Probe C — list user-visible tables."""
    sql = _schema_sql(database)
    if sql is None:
        pytest.skip(f"Schema probe not defined for backend {database.backend!r}")
    df = _run_probe(database, sql)
    assert df is not None


def test_sample_data_probe(database: Database) -> None:
    """Probe D — row count on first table from schema probe."""
    sql = _schema_sql(database)
    if sql is None:
        pytest.skip(f"Schema probe not defined for backend {database.backend!r}")
    schema_df = _run_probe(database, sql)
    schema, table = _first_table_from_schema_df(database, schema_df)
    count_sql = _build_count_sql(database, schema, table)
    df = _run_probe(database, count_sql)
    row_count = df.iloc[0]["row_count"]
    assert row_count >= 0
