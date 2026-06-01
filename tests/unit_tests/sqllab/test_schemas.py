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
import pytest
from marshmallow import ValidationError

from superset.sqllab.schemas import (
    EstimateQueryCostSchema,
    ExecutePayloadSchema,
    FormatQueryPayloadSchema,
)


def test_estimate_query_cost_schema_valid() -> None:
    result = EstimateQueryCostSchema().load({"database_id": 1, "sql": "SELECT 1"})
    assert result["database_id"] == 1
    assert result["sql"] == "SELECT 1"


def test_estimate_query_cost_schema_with_optional_fields() -> None:
    result = EstimateQueryCostSchema().load(
        {
            "database_id": 1,
            "sql": "SELECT * FROM t",
            "template_params": {"param1": "value1"},
            "catalog": "my_catalog",
            "schema": "public",
        }
    )
    assert result["template_params"] == {"param1": "value1"}
    assert result["catalog"] == "my_catalog"
    assert result["schema"] == "public"


def test_estimate_query_cost_schema_missing_database_id() -> None:
    with pytest.raises(ValidationError) as exc_info:
        EstimateQueryCostSchema().load({"sql": "SELECT 1"})
    assert "database_id" in exc_info.value.messages


def test_estimate_query_cost_schema_missing_sql() -> None:
    with pytest.raises(ValidationError) as exc_info:
        EstimateQueryCostSchema().load({"database_id": 1})
    assert "sql" in exc_info.value.messages


def test_format_query_payload_schema_valid() -> None:
    result = FormatQueryPayloadSchema().load({"sql": "SELECT 1"})
    assert result["sql"] == "SELECT 1"


def test_format_query_payload_schema_with_engine() -> None:
    result = FormatQueryPayloadSchema().load(
        {"sql": "SELECT 1", "engine": "postgresql"}
    )
    assert result["engine"] == "postgresql"


def test_format_query_payload_schema_with_database_id() -> None:
    result = FormatQueryPayloadSchema().load({"sql": "SELECT 1", "database_id": 5})
    assert result["database_id"] == 5


def test_format_query_payload_schema_missing_sql() -> None:
    with pytest.raises(ValidationError) as exc_info:
        FormatQueryPayloadSchema().load({})
    assert "sql" in exc_info.value.messages


def test_execute_payload_schema_valid_minimal() -> None:
    result = ExecutePayloadSchema().load({"database_id": 1, "sql": "SELECT 1"})
    assert result["database_id"] == 1
    assert result["sql"] == "SELECT 1"


def test_execute_payload_schema_valid_full() -> None:
    result = ExecutePayloadSchema().load(
        {
            "database_id": 1,
            "sql": "SELECT * FROM users",
            "client_id": "abc123",
            "queryLimit": 100,
            "sql_editor_id": "editor_1",
            "catalog": "default",
            "schema": "public",
            "tab": "Query 1",
            "ctas_method": "TABLE",
            "templateParams": '{"key": "val"}',
            "tmp_table_name": "tmp_results",
            "select_as_cta": True,
            "runAsync": True,
            "expand_data": True,
        }
    )
    assert result["client_id"] == "abc123"
    assert result["queryLimit"] == 100
    assert result["runAsync"] is True
    assert result["expand_data"] is True


def test_execute_payload_schema_missing_database_id() -> None:
    with pytest.raises(ValidationError) as exc_info:
        ExecutePayloadSchema().load({"sql": "SELECT 1"})
    assert "database_id" in exc_info.value.messages


def test_execute_payload_schema_missing_sql() -> None:
    with pytest.raises(ValidationError) as exc_info:
        ExecutePayloadSchema().load({"database_id": 1})
    assert "sql" in exc_info.value.messages


def test_execute_payload_schema_nullable_fields() -> None:
    result = ExecutePayloadSchema().load(
        {
            "database_id": 1,
            "sql": "SELECT 1",
            "client_id": None,
            "schema": None,
            "tab": None,
        }
    )
    assert result["client_id"] is None
    assert result["schema"] is None
    assert result["tab"] is None
