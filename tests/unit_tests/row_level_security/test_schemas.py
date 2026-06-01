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

from superset.row_level_security.schemas import (
    RLSPostSchema,
    RLSPutSchema,
)
from superset.utils.core import RowLevelSecurityFilterType


def test_rls_post_schema_valid_regular() -> None:
    result = RLSPostSchema().load(
        {
            "name": "test_filter",
            "filter_type": RowLevelSecurityFilterType.REGULAR.value,
            "tables": [1],
            "roles": [1, 2],
            "clause": "id = 1",
        }
    )
    assert result["name"] == "test_filter"
    assert result["filter_type"] == RowLevelSecurityFilterType.REGULAR.value
    assert result["tables"] == [1]
    assert result["roles"] == [1, 2]
    assert result["clause"] == "id = 1"


def test_rls_post_schema_valid_base() -> None:
    result = RLSPostSchema().load(
        {
            "name": "base_filter",
            "filter_type": RowLevelSecurityFilterType.BASE.value,
            "tables": [1, 2],
            "roles": [],
            "clause": "1 = 0",
        }
    )
    assert result["filter_type"] == RowLevelSecurityFilterType.BASE.value


def test_rls_post_schema_with_optional_fields() -> None:
    result = RLSPostSchema().load(
        {
            "name": "filter_with_options",
            "filter_type": RowLevelSecurityFilterType.REGULAR.value,
            "tables": [1],
            "roles": [1],
            "clause": "dept = 'finance'",
            "group_key": "department",
            "description": "Filter for finance department",
        }
    )
    assert result["group_key"] == "department"
    assert result["description"] == "Filter for finance department"


def test_rls_post_schema_missing_name() -> None:
    with pytest.raises(ValidationError) as exc_info:
        RLSPostSchema().load(
            {
                "filter_type": RowLevelSecurityFilterType.REGULAR.value,
                "tables": [1],
                "roles": [1],
                "clause": "id = 1",
            }
        )
    assert "name" in exc_info.value.messages


def test_rls_post_schema_empty_name() -> None:
    with pytest.raises(ValidationError):
        RLSPostSchema().load(
            {
                "name": "",
                "filter_type": RowLevelSecurityFilterType.REGULAR.value,
                "tables": [1],
                "roles": [1],
                "clause": "id = 1",
            }
        )


def test_rls_post_schema_name_too_long() -> None:
    with pytest.raises(ValidationError):
        RLSPostSchema().load(
            {
                "name": "x" * 256,
                "filter_type": RowLevelSecurityFilterType.REGULAR.value,
                "tables": [1],
                "roles": [1],
                "clause": "id = 1",
            }
        )


def test_rls_post_schema_invalid_filter_type() -> None:
    with pytest.raises(ValidationError) as exc_info:
        RLSPostSchema().load(
            {
                "name": "test",
                "filter_type": "INVALID",
                "tables": [1],
                "roles": [1],
                "clause": "id = 1",
            }
        )
    assert "filter_type" in exc_info.value.messages


def test_rls_post_schema_missing_tables() -> None:
    with pytest.raises(ValidationError) as exc_info:
        RLSPostSchema().load(
            {
                "name": "test",
                "filter_type": RowLevelSecurityFilterType.REGULAR.value,
                "roles": [1],
                "clause": "id = 1",
            }
        )
    assert "tables" in exc_info.value.messages


def test_rls_post_schema_empty_tables() -> None:
    with pytest.raises(ValidationError):
        RLSPostSchema().load(
            {
                "name": "test",
                "filter_type": RowLevelSecurityFilterType.REGULAR.value,
                "tables": [],
                "roles": [1],
                "clause": "id = 1",
            }
        )


def test_rls_post_schema_missing_clause() -> None:
    with pytest.raises(ValidationError) as exc_info:
        RLSPostSchema().load(
            {
                "name": "test",
                "filter_type": RowLevelSecurityFilterType.REGULAR.value,
                "tables": [1],
                "roles": [1],
            }
        )
    assert "clause" in exc_info.value.messages


def test_rls_put_schema_empty() -> None:
    result = RLSPutSchema().load({})
    assert result == {}


def test_rls_put_schema_partial_update_name() -> None:
    result = RLSPutSchema().load({"name": "updated_name"})
    assert result["name"] == "updated_name"


def test_rls_put_schema_partial_update_clause() -> None:
    result = RLSPutSchema().load({"clause": "new_col = 'value'"})
    assert result["clause"] == "new_col = 'value'"


def test_rls_put_schema_invalid_filter_type() -> None:
    with pytest.raises(ValidationError):
        RLSPutSchema().load({"filter_type": "NOT_A_TYPE"})


def test_rls_put_schema_name_too_long() -> None:
    with pytest.raises(ValidationError):
        RLSPutSchema().load({"name": "x" * 256})


def test_rls_put_schema_group_key_null() -> None:
    result = RLSPutSchema().load({"group_key": None})
    assert result["group_key"] is None


def test_rls_put_schema_description_null() -> None:
    result = RLSPutSchema().load({"description": None})
    assert result["description"] is None
