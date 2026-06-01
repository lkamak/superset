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
from superset.sqllab.command_status import SqlJsonExecutionStatus


def test_sql_json_execution_status_values() -> None:
    assert SqlJsonExecutionStatus.QUERY_ALREADY_CREATED.value == 1
    assert SqlJsonExecutionStatus.HAS_RESULTS.value == 2
    assert SqlJsonExecutionStatus.QUERY_IS_RUNNING.value == 3
    assert SqlJsonExecutionStatus.FAILED.value == 4


def test_sql_json_execution_status_members() -> None:
    members = list(SqlJsonExecutionStatus)
    assert len(members) == 4


def test_sql_json_execution_status_identity() -> None:
    assert SqlJsonExecutionStatus(1) is SqlJsonExecutionStatus.QUERY_ALREADY_CREATED
    assert SqlJsonExecutionStatus(2) is SqlJsonExecutionStatus.HAS_RESULTS
    assert SqlJsonExecutionStatus(3) is SqlJsonExecutionStatus.QUERY_IS_RUNNING
    assert SqlJsonExecutionStatus(4) is SqlJsonExecutionStatus.FAILED
