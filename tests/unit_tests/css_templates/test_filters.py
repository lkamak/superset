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
from unittest.mock import MagicMock, patch

from superset.css_templates.filters import CssTemplateAllTextFilter


def _make_filter() -> CssTemplateAllTextFilter:
    return CssTemplateAllTextFilter("template_name", MagicMock())


def test_css_template_all_text_filter_name() -> None:
    filter_instance = _make_filter()
    assert filter_instance.arg_name == "css_template_all_text"


def test_css_template_all_text_filter_empty_value() -> None:
    filter_instance = _make_filter()
    mock_query = MagicMock()
    result = filter_instance.apply(mock_query, "")
    assert result == mock_query


def test_css_template_all_text_filter_none_value() -> None:
    filter_instance = _make_filter()
    mock_query = MagicMock()
    result = filter_instance.apply(mock_query, None)
    assert result == mock_query


@patch("superset.css_templates.filters.or_")
@patch("superset.css_templates.filters.CssTemplate")
def test_css_template_all_text_filter_with_value(
    mock_css_template: MagicMock, mock_or: MagicMock
) -> None:
    mock_css_template.template_name = MagicMock()
    mock_css_template.css = MagicMock()

    filter_instance = _make_filter()
    mock_query = MagicMock()
    filter_instance.apply(mock_query, "test")

    mock_css_template.template_name.ilike.assert_called_once_with("%test%")
    mock_css_template.css.ilike.assert_called_once_with("%test%")
    mock_query.filter.assert_called_once()
