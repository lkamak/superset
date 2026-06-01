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

from superset.cachekeys.schemas import CacheInvalidationRequestSchema, Datasource
from superset.utils.core import DatasourceType


def test_cache_invalidation_schema_with_uids() -> None:
    result = CacheInvalidationRequestSchema().load(
        {"datasource_uids": ["uid1", "uid2"]}
    )
    assert result["datasource_uids"] == ["uid1", "uid2"]


def test_cache_invalidation_schema_with_datasources() -> None:
    result = CacheInvalidationRequestSchema().load(
        {
            "datasources": [
                {
                    "database_name": "main",
                    "datasource_name": "my_table",
                    "schema": "public",
                    "datasource_type": DatasourceType.TABLE.value,
                }
            ]
        }
    )
    assert len(result["datasources"]) == 1
    assert result["datasources"][0]["database_name"] == "main"


def test_cache_invalidation_schema_empty() -> None:
    result = CacheInvalidationRequestSchema().load({})
    assert "datasource_uids" not in result
    assert "datasources" not in result


def test_cache_invalidation_schema_with_both() -> None:
    result = CacheInvalidationRequestSchema().load(
        {
            "datasource_uids": ["uid1"],
            "datasources": [
                {
                    "datasource_name": "t1",
                    "datasource_type": DatasourceType.TABLE.value,
                }
            ],
        }
    )
    assert result["datasource_uids"] == ["uid1"]
    assert len(result["datasources"]) == 1


def test_datasource_schema_valid() -> None:
    result = Datasource().load(
        {
            "database_name": "db1",
            "datasource_name": "table1",
            "schema": "public",
            "datasource_type": DatasourceType.TABLE.value,
        }
    )
    assert result["datasource_type"] == DatasourceType.TABLE.value


def test_datasource_schema_invalid_type() -> None:
    with pytest.raises(ValidationError):
        Datasource().load(
            {
                "datasource_name": "table1",
                "datasource_type": "invalid_type",
            }
        )


def test_datasource_schema_with_catalog() -> None:
    result = Datasource().load(
        {
            "datasource_name": "table1",
            "catalog": "my_catalog",
            "datasource_type": DatasourceType.TABLE.value,
        }
    )
    assert result["catalog"] == "my_catalog"


def test_datasource_schema_catalog_none() -> None:
    result = Datasource().load(
        {
            "datasource_name": "table1",
            "catalog": None,
            "datasource_type": DatasourceType.TABLE.value,
        }
    )
    assert result["catalog"] is None
