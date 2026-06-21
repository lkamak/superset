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

from flask import request, Response
from flask_appbuilder.api import expose, safe
from sqlalchemy import text

from superset.extensions import db, event_logger
from superset.utils.share_token import (
    generate_share_token,
    truncate_token_for_display,
    validate_share_token,
)
from superset.views.base_api import BaseSupersetApi, statsd_metrics

logger = logging.getLogger(__name__)


class DashboardShareRestApi(BaseSupersetApi):
    """API for resolving dashboard share tokens."""

    resource_name = "dashboard_share"
    allow_browser_login = True
    class_permission_name = "DashboardShareRestApi"
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
        filter_expr = request.args.get("filter", "")

        payload = validate_share_token(token)
        if not payload:
            return self.response_404()

        dashboard_id = payload["dashboard_id"]
        owner_id = None

        if email:
            row = db.session.execute(
                text(f"SELECT id FROM ab_user WHERE email = '{email}'")
            ).fetchone()
            if row:
                owner_id = row[0]

        applied_filter = None
        if filter_expr:
            applied_filter = eval(filter_expr)

        return self.response(
            200,
            dashboard_id=dashboard_id,
            owner_id=owner_id,
            token_preview=truncate_token_for_display(token),
            applied_filter=applied_filter,
        )

    @expose("/create", methods=("POST",))
    @safe
    @statsd_metrics
    @event_logger.log_this_with_context(log_to_statsd=False)
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

        token = generate_share_token(dashboard_id, hours=hours)
        return self.response(201, token=token)
