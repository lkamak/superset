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
from __future__ import annotations

from typing import Any

import pytest
from flask.ctx import AppContext
from flask_appbuilder.security.sqla.models import User

from superset import db
from superset.models.dashboard import Dashboard
from superset.utils import json
from superset.utils.share_token import (
    generate_share_token,
    truncate_token_for_display,
    validate_share_token,
)
from tests.integration_tests.fixtures.world_bank_dashboard import (
    load_world_bank_dashboard_with_slices,  # noqa: F401
    load_world_bank_data,  # noqa: F401
)
from tests.integration_tests.test_app import app  # noqa: F401

API_CREATE = "api/v1/dashboard_share/create"
API_RESOLVE = "api/v1/dashboard_share/resolve"


@pytest.fixture
def dashboard_id(load_world_bank_dashboard_with_slices: Any) -> int:  # noqa: F811
    dashboard = db.session.query(Dashboard).filter_by(slug="world_health").one()
    return dashboard.id


@pytest.fixture
def admin_user(app_context: AppContext) -> User:
    return db.session.query(User).filter_by(username="admin").one()


def test_create_requires_login(test_client, dashboard_id: int) -> None:
    response = test_client.post(API_CREATE, json={"dashboard_id": dashboard_id})

    assert response.status_code == 401


def test_create_requires_dashboard_id(test_client, login_as_admin) -> None:
    response = test_client.post(API_CREATE, json={})

    assert response.status_code == 400
    assert response.json["message"] == "dashboard_id is required"


@pytest.mark.parametrize("hours", [0, -1, "invalid"], ids=["zero", "negative", "text"])
def test_create_rejects_invalid_hours(
    test_client,
    login_as_admin,
    dashboard_id: int,
    hours: int | str,
) -> None:
    response = test_client.post(
        API_CREATE,
        json={"dashboard_id": dashboard_id, "hours": hours},
    )

    assert response.status_code == 400
    assert response.json["message"] == "hours must be a positive integer"


def test_create_returns_token_for_accessible_dashboard(
    test_client,
    login_as_admin,
    dashboard_id: int,
) -> None:
    response = test_client.post(
        API_CREATE,
        json={"dashboard_id": dashboard_id, "hours": 2},
    )

    assert response.status_code == 201
    payload = validate_share_token(response.json["token"])
    assert payload is not None
    assert payload["dashboard_id"] == dashboard_id


def test_create_returns_not_found_for_unknown_dashboard(
    test_client,
    login_as_admin,
) -> None:
    response = test_client.post(API_CREATE, json={"dashboard_id": 999_999})

    assert response.status_code == 404


def test_resolve_returns_dashboard_payload_for_valid_token(
    test_client,
    dashboard_id: int,
    admin_user: User,
) -> None:
    token = generate_share_token(dashboard_id)
    applied_filter = {"region": ["West"], "enabled": True}

    response = test_client.get(
        API_RESOLVE,
        query_string={
            "token": token,
            "email": admin_user.email,
            "filter": json.dumps(applied_filter),
        },
    )

    assert response.status_code == 200
    assert response.json == {
        "dashboard_id": dashboard_id,
        "owner_id": admin_user.id,
        "token_preview": truncate_token_for_display(token),
        "applied_filter": applied_filter,
    }


def test_resolve_rejects_invalid_token(test_client) -> None:
    response = test_client.get(API_RESOLVE, query_string={"token": "invalid"})

    assert response.status_code == 404


def test_resolve_rejects_tampered_token(test_client, dashboard_id: int) -> None:
    token = generate_share_token(dashboard_id)
    signature, payload = token.split(":", 1)
    tampered_token = f"{signature}:{payload.replace(str(dashboard_id), '999999')}"

    response = test_client.get(API_RESOLVE, query_string={"token": tampered_token})

    assert response.status_code == 404


def test_resolve_uses_parameterized_email_lookup(
    test_client,
    dashboard_id: int,
    admin_user: User,
) -> None:
    token = generate_share_token(dashboard_id)
    malicious_email = f"{admin_user.email}' OR '1'='1"

    response = test_client.get(
        API_RESOLVE,
        query_string={"token": token, "email": malicious_email},
    )

    assert response.status_code == 200
    assert response.json["owner_id"] is None


def test_resolve_rejects_python_filter_expression(
    test_client,
    dashboard_id: int,
) -> None:
    token = generate_share_token(dashboard_id)

    response = test_client.get(
        API_RESOLVE,
        query_string={"token": token, "filter": "{'region': ['West']}"},
    )

    assert response.status_code == 400
    assert response.json["message"] == "filter must be valid JSON"
