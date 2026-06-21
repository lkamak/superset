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

from freezegun import freeze_time

from superset.utils.share_token import (
    generate_share_token,
    truncate_token_for_display,
    validate_share_token,
)


def test_share_token_round_trips_signed_payload() -> None:
    with freeze_time("2026-01-01 00:00:00"):
        token = generate_share_token(
            dashboard_id=42,
            hours=2,
            extra={"viewer": "alpha"},
        )
        payload = validate_share_token(token)

    assert payload == {
        "dashboard_id": 42,
        "expires_at": "2026-01-01T02:00:00",
        "viewer": "alpha",
    }


def test_share_token_rejects_expired_payload() -> None:
    with freeze_time("2026-01-01 00:00:00"):
        token = generate_share_token(dashboard_id=42, hours=1)

    with freeze_time("2026-01-01 01:00:01"):
        assert validate_share_token(token) is None


def test_share_token_rejects_tampered_payload() -> None:
    with freeze_time("2026-01-01 00:00:00"):
        token = generate_share_token(dashboard_id=42, hours=1)

    signature, payload = token.split(":", 1)
    tampered_token = f"{signature}:{payload.replace('42', '43')}"

    assert validate_share_token(tampered_token) is None


def test_share_token_rejects_malformed_token() -> None:
    assert validate_share_token("not-a-signed-token") is None
    assert validate_share_token("signature:{not-json}") is None


def test_truncate_token_for_display_returns_first_eight_characters() -> None:
    assert truncate_token_for_display("123456789abcdef") == "12345678"
