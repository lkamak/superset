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
import json  # noqa: TID251
from unittest.mock import MagicMock

from superset.sqllab.command_status import SqlJsonExecutionStatus
from superset.sqllab.execution_context_convertor import ExecutionContextConvertor


def test_set_max_row_in_display() -> None:
    convertor = ExecutionContextConvertor()
    convertor.set_max_row_in_display(100)
    assert convertor._max_row_in_display_configuration == 100


def test_set_payload_has_results() -> None:
    convertor = ExecutionContextConvertor()
    mock_context = MagicMock()
    mock_context.get_execution_result.return_value = {"data": [1, 2, 3]}

    convertor.set_payload(mock_context, SqlJsonExecutionStatus.HAS_RESULTS)
    assert convertor.payload == {"data": [1, 2, 3]}
    assert convertor._exc_status == SqlJsonExecutionStatus.HAS_RESULTS


def test_set_payload_query_is_running() -> None:
    convertor = ExecutionContextConvertor()
    mock_context = MagicMock()
    mock_context.query.to_dict.return_value = {"id": 1, "state": "running"}

    convertor.set_payload(mock_context, SqlJsonExecutionStatus.QUERY_IS_RUNNING)
    assert convertor.payload == {"id": 1, "state": "running"}
    assert convertor._exc_status == SqlJsonExecutionStatus.QUERY_IS_RUNNING


def test_set_payload_has_results_none() -> None:
    convertor = ExecutionContextConvertor()
    mock_context = MagicMock()
    mock_context.get_execution_result.return_value = None

    convertor.set_payload(mock_context, SqlJsonExecutionStatus.HAS_RESULTS)
    assert convertor.payload == {}


def test_serialize_payload_has_results() -> None:
    convertor = ExecutionContextConvertor()
    convertor.set_max_row_in_display(10)

    mock_context = MagicMock()
    mock_context.get_execution_result.return_value = {
        "status": "success",
        "query": {"rows": 2},
        "data": [{"col": 1}, {"col": 2}],
    }
    convertor.set_payload(mock_context, SqlJsonExecutionStatus.HAS_RESULTS)

    serialized = convertor.serialize_payload()
    parsed = json.loads(serialized)
    assert parsed["data"] == [{"col": 1}, {"col": 2}]


def test_serialize_payload_not_has_results() -> None:
    convertor = ExecutionContextConvertor()
    convertor.set_max_row_in_display(10)

    mock_context = MagicMock()
    mock_context.query.to_dict.return_value = {"id": 42, "state": "running"}
    convertor.set_payload(mock_context, SqlJsonExecutionStatus.QUERY_IS_RUNNING)

    serialized = convertor.serialize_payload()
    parsed = json.loads(serialized)
    assert parsed == {"query": {"id": 42, "state": "running"}}


def test_serialize_payload_applies_display_limit() -> None:
    convertor = ExecutionContextConvertor()
    convertor.set_max_row_in_display(2)

    mock_context = MagicMock()
    mock_context.get_execution_result.return_value = {
        "status": "success",
        "query": {"rows": 5},
        "data": [{"v": i} for i in range(5)],
    }
    convertor.set_payload(mock_context, SqlJsonExecutionStatus.HAS_RESULTS)

    serialized = convertor.serialize_payload()
    parsed = json.loads(serialized)
    assert len(parsed["data"]) == 2
    assert parsed["displayLimitReached"] is True
