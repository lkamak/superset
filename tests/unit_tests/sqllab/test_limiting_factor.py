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
from superset.sqllab.limiting_factor import LimitingFactor


def test_limiting_factor_values() -> None:
    assert LimitingFactor.QUERY == "QUERY"
    assert LimitingFactor.DROPDOWN == "DROPDOWN"
    assert LimitingFactor.QUERY_AND_DROPDOWN == "QUERY_AND_DROPDOWN"
    assert LimitingFactor.NOT_LIMITED == "NOT_LIMITED"
    assert LimitingFactor.UNKNOWN == "UNKNOWN"


def test_limiting_factor_member_count() -> None:
    assert len(LimitingFactor) == 5


def test_limiting_factor_is_str() -> None:
    assert isinstance(LimitingFactor.QUERY, str)
    assert isinstance(LimitingFactor.NOT_LIMITED, str)


def test_limiting_factor_string_comparison() -> None:
    assert LimitingFactor.QUERY == "QUERY"
    assert "DROPDOWN" == LimitingFactor.DROPDOWN
