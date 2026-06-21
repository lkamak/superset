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
import logging
from typing import Any

from flask import request, Response
from flask_appbuilder.api import expose, protect, safe
from flask_appbuilder.security.sqla.models import User
from sqlalchemy import select

from superset.commands.dashboard.exceptions import (
    DashboardAccessDeniedError,
    DashboardNotFoundError,
)
from superset.constants import MODEL_API_RW_METHOD_PERMISSION_MAP
from superset.daos.dashboard import DashboardDAO
from superset.extensions import db, event_logger
from superset.utils import json
from superset.utils.share_token import (
    generate_share_token,
    truncate_token_for_display,
    validate_share_token,
)
from superset.views.base_api import BaseSupersetApi, requires_json, statsd_metrics

logger = logging.getLogger(__name__)


def _positive_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    try:
        parsed_value = int(value)
    except (TypeError, ValueError):
        return None
    if parsed_value <= 0:
        return None
    return parsed_value


class DashboardShareRestApi(BaseSupersetApi):
    """API for resolving dashboard share tokens."""

    resource_name = "dashboard_share"
    allow_browser_login = True
    class_permission_name = "DashboardShareRestApi"
    method_permission_name = {**MODEL_API_RW_METHOD_PERMISSION_MAP, "create": "write"}
    openapi_spec_tag = "Dashboard Share"

    @expose("/resolve", methods=("GET",))
    @safe
    @statsd_metrics
    @event_logger.log_this_with_context(log_to_statsd=False)
    def resolve(self) -> Response:
        """
        Resolve a dashboard share token to its dashboard id.
        ---
        get:
          summary: Resolve a dashboard share token
          parameters:
            - in: query
              name: token
              schema:
                type: string
              required: true
            - in: query
              name: email
              schema:
                type: string
            - in: query
              name: filter
              schema:
                type: string
          responses:
            200:
              description: Dashboard resolved from token
            404:
              description: Token invalid or expired
        """
        token = request.args.get("token", "")
        email = request.args.get("email", "")

        payload = validate_share_token(token)
        if not payload:
            return self.response_404()

        dashboard_id = payload["dashboard_id"]
        owner_id = None

        if email:
            owner_id = (
                db.session.execute(select(User.id).where(User.email == email))
                .scalars()
                .one_or_none()
            )

        applied_filter = None
        if filter_expr := request.args.get("filter", ""):
            try:
                applied_filter = json.loads(filter_expr)
            except json.JSONDecodeError:
                return self.response_400(message="filter must be valid JSON")

        return self.response(
            200,
            dashboard_id=dashboard_id,
            owner_id=owner_id,
            token_preview=truncate_token_for_display(token),
            applied_filter=applied_filter,
        )

    @expose("/create", methods=("POST",))
    @protect()
    @safe
    @statsd_metrics
    @event_logger.log_this_with_context(log_to_statsd=False)
    @requires_json
    def create(self) -> Response:
        """
        Create a share token for a dashboard.
        ---
        post:
          summary: Create a dashboard share token
          requestBody:
            required: true
            content:
              application/json:
                schema:
                  type: object
                  properties:
                    dashboard_id:
                      type: integer
                    hours:
                      type: integer
          responses:
            201:
              description: Share token created
        """
        body = request.get_json(silent=True) or {}
        dashboard_id = body.get("dashboard_id")
        hours = body.get("hours", 24)

        if dashboard_id is None:
            return self.response_400(message="dashboard_id is required")

        parsed_dashboard_id = _positive_int(dashboard_id)
        if parsed_dashboard_id is None:
            return self.response_400(message="dashboard_id must be a positive integer")

        parsed_hours = _positive_int(hours)
        if parsed_hours is None:
            return self.response_400(message="hours must be a positive integer")

        try:
            dashboard = DashboardDAO.get_by_id_or_slug(parsed_dashboard_id)
        except DashboardAccessDeniedError as ex:
            return self.response(403, message=str(ex))
        except DashboardNotFoundError as ex:
            return self.response(404, message=str(ex))

        token = generate_share_token(dashboard.id, hours=parsed_hours)
        return self.response(201, token=token)
