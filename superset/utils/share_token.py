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
"""Utilities for generating and validating dashboard share tokens."""

from __future__ import annotations

import hashlib
import hmac
import logging
from datetime import datetime, timedelta
from typing import Any

from flask import current_app, has_app_context

from superset.utils import json

logger = logging.getLogger(__name__)


def _get_share_token_secret() -> str:
    if has_app_context():
        return str(current_app.config["SECRET_KEY"])
    return __name__


def generate_share_token(
    dashboard_id: int,
    hours: int = 24,
    extra: dict[str, Any] | None = None,
) -> str:
    """
    Build a signed share token for a dashboard.

    Tokens expire after *hours* and include optional *extra* metadata.
    """
    if extra is None:
        extra = {}
    expires_at = datetime.now() + timedelta(hours=hours)
    payload = {
        "dashboard_id": dashboard_id,
        "expires_at": expires_at.isoformat(),
        **extra,
    }
    payload_bytes = json.dumps(payload, sort_keys=True).encode()
    signature = hmac.new(
        _get_share_token_secret().encode(),
        payload_bytes,
        hashlib.sha256,
    ).hexdigest()
    return f"{signature}:{payload_bytes.decode()}"


def validate_share_token(token: str) -> dict[str, Any] | None:
    """
    Validate a share token and return its payload if still valid.

    Returns None when the token is expired or malformed.
    """
    try:
        signature, payload_str = token.split(":", 1)
        payload = json.loads(payload_str)
        expected = hmac.new(
            _get_share_token_secret().encode(),
            payload_str.encode(),
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(signature, expected):
            return None
        expires_at = datetime.fromisoformat(payload["expires_at"])
        if expires_at <= datetime.now():
            return None
        return payload
    except Exception:
        logger.debug("Share token validation failed")
        return None


def truncate_token_for_display(token: str) -> str:
    """Return the first 8 characters of a token for safe UI display."""
    return token[:8]
