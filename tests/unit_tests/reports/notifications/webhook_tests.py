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

import socket

import pandas as pd
import pytest

from superset.reports.notifications.exceptions import (
    NotificationParamException,
)
from superset.reports.notifications.webhook import WebhookNotification
from superset.utils.core import HeaderDataType


class MockResponse:
    status_code = 200
    text = ""


def fail_post(*_args: object, **_kwargs: object) -> None:
    pytest.fail("requests.post should not be called")


@pytest.fixture
def mock_header_data() -> HeaderDataType:
    return {
        "notification_format": "PNG",
        "notification_type": "Alert",
        "owners": [1],
        "notification_source": None,
        "chart_id": None,
        "dashboard_id": None,
        "slack_channels": None,
        "execution_id": "test-execution-id",
    }


def build_webhook_notification(
    mock_header_data: HeaderDataType,
    target: str,
) -> WebhookNotification:
    from superset.reports.models import ReportRecipients, ReportRecipientType
    from superset.reports.notifications.base import NotificationContent

    content = NotificationContent(
        name="test alert",
        header_data=mock_header_data,
        description="Test description",
    )
    return WebhookNotification(
        recipient=ReportRecipients(
            type=ReportRecipientType.WEBHOOK,
            recipient_config_json=f'{{"target": "{target}"}}',
        ),
        content=content,
    )


def enable_webhook_feature(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "superset.reports.notifications.webhook.feature_flag_manager.is_feature_enabled",
        lambda _flag: True,
    )


def set_webhook_config(
    monkeypatch: pytest.MonkeyPatch,
    config: dict[str, object],
) -> None:
    mock_current_app = type("MockCurrentApp", (), {"config": config})
    monkeypatch.setattr(
        "superset.reports.notifications.webhook.current_app", mock_current_app
    )


def set_webhook_dns(
    monkeypatch: pytest.MonkeyPatch,
    addresses: list[str],
) -> None:
    def getaddrinfo(
        _host: str,
        port: int | None,
        *_args: object,
        **_kwargs: object,
    ) -> list[tuple[int, int, int, str, tuple[str, int]]]:
        return [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", (address, port or 443))
            for address in addresses
        ]

    monkeypatch.setattr(
        "superset.reports.notifications.webhook.socket.getaddrinfo", getaddrinfo
    )


def set_webhook_dns_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    def getaddrinfo(
        _host: str,
        _port: int | None,
        *_args: object,
        **_kwargs: object,
    ) -> None:
        raise socket.gaierror("Name or service not known")

    monkeypatch.setattr(
        "superset.reports.notifications.webhook.socket.getaddrinfo", getaddrinfo
    )


def test_get_webhook_url(mock_header_data) -> None:
    """
    Test the _get_webhook_url function to ensure it correctly extracts
    the webhook URL from recipient configuration
    """
    from superset.reports.models import ReportRecipients, ReportRecipientType
    from superset.reports.notifications.base import NotificationContent

    content = NotificationContent(
        name="test alert",
        header_data=mock_header_data,
        embedded_data=pd.DataFrame({"A": [1, 2, 3], "B": [4, 5, 6]}),
        description="Test description",
    )
    webhook_notification = WebhookNotification(
        recipient=ReportRecipients(
            type=ReportRecipientType.WEBHOOK,
            recipient_config_json='{"target": "https://example.com/webhook"}',
        ),
        content=content,
    )

    result = webhook_notification._get_webhook_url()

    assert result == "https://example.com/webhook"


def test_get_webhook_url_missing_url(mock_header_data) -> None:
    """
    Test that _get_webhook_url raises an exception when URL is missing
    """
    from superset.reports.models import ReportRecipients, ReportRecipientType
    from superset.reports.notifications.base import NotificationContent

    content = NotificationContent(
        name="test alert",
        header_data=mock_header_data,
        description="Test description",
    )
    webhook_notification = WebhookNotification(
        recipient=ReportRecipients(
            type=ReportRecipientType.WEBHOOK,
            recipient_config_json="{}",
        ),
        content=content,
    )

    with pytest.raises(NotificationParamException, match="Webhook URL is required"):
        webhook_notification._get_webhook_url()


def test_get_req_payload_basic(mock_header_data) -> None:
    """
    Test that _get_req_payload returns correct payload structure
    """
    from superset.reports.models import ReportRecipients, ReportRecipientType
    from superset.reports.notifications.base import NotificationContent

    content = NotificationContent(
        name="Payload Name",
        header_data=mock_header_data,
        embedded_data=None,
        description="Payload Description",
        url="http://example.com/report",
        text="Report Text",
    )
    webhook_notification = WebhookNotification(
        recipient=ReportRecipients(
            type=ReportRecipientType.WEBHOOK,
            recipient_config_json='{"target": "https://webhook.com"}',
        ),
        content=content,
    )

    payload = webhook_notification._get_req_payload()

    assert payload["name"] == "Payload Name"
    assert payload["description"] == "Payload Description"
    assert payload["url"] == "http://example.com/report"
    assert payload["text"] == "Report Text"
    assert isinstance(payload["header"], dict)
    # Optional fields from header_data
    assert payload["header"]["notification_format"] == "PNG"
    assert payload["header"]["notification_type"] == "Alert"


def test_get_files_includes_all_content_types(mock_header_data) -> None:
    """
    Test that _get_files correctly includes csv, pdf, and multiple screenshot attachments
    """  # noqa: E501

    from superset.reports.models import ReportRecipients, ReportRecipientType
    from superset.reports.notifications.base import NotificationContent

    csv_bytes = b"col1,col2\n1,2"
    pdf_bytes = b"%PDF-1.4"
    screenshots = [b"fakeimg1", b"fakeimg2"]

    content = NotificationContent(
        name="file test",
        header_data=mock_header_data,
        csv=csv_bytes,
        pdf=pdf_bytes,
        screenshots=screenshots,
        description="files test",
    )
    webhook_notification = WebhookNotification(
        recipient=ReportRecipients(
            type=ReportRecipientType.WEBHOOK,
            recipient_config_json='{"target": "https://webhook.com"}',
        ),
        content=content,
    )
    files = webhook_notification._get_files()
    # There should be 1 csv, 1 pdf, and 2 screenshots = 4 files total
    assert len(files) == 4

    file_names = [file_info[1][0] for file_info in files]
    assert "report.csv" in file_names
    assert "report.pdf" in file_names
    assert "screenshot_0.png" in file_names
    assert "screenshot_1.png" in file_names

    mime_types = [file_info[1][2] for file_info in files]
    assert "text/csv" in mime_types
    assert "application/pdf" in mime_types
    assert mime_types.count("image/png") == 2


def test_get_files_empty_when_no_content(mock_header_data) -> None:
    """
    Test that _get_files returns empty list when no files present
    """
    from superset.reports.models import ReportRecipients, ReportRecipientType
    from superset.reports.notifications.base import NotificationContent

    content = NotificationContent(
        name="no files",
        header_data=mock_header_data,
        description="no files test",
    )
    webhook_notification = WebhookNotification(
        recipient=ReportRecipients(
            type=ReportRecipientType.WEBHOOK,
            recipient_config_json='{"target": "https://webhook.com"}',
        ),
        content=content,
    )
    files = webhook_notification._get_files()
    assert files == []


def test_send_http_only_https_check(monkeypatch, mock_header_data) -> None:
    """
    Test send raises when URL is not HTTPS and config enforces HTTPS only
    """
    from superset.reports.models import ReportRecipients, ReportRecipientType
    from superset.reports.notifications.base import NotificationContent

    content = NotificationContent(
        name="test alert", header_data=mock_header_data, description="Test description"
    )
    webhook_notification = WebhookNotification(
        recipient=ReportRecipients(
            type=ReportRecipientType.WEBHOOK,
            recipient_config_json='{"target": "http://notsecure.com/webhook"}',
        ),
        content=content,
    )

    class MockCurrentApp:
        config = {"ALERT_REPORTS_WEBHOOK_HTTPS_ONLY": True}

    monkeypatch.setattr(
        "superset.reports.notifications.webhook.current_app", MockCurrentApp
    )
    monkeypatch.setattr(
        "superset.reports.notifications.webhook.feature_flag_manager.is_feature_enabled",
        lambda flag: True,
    )

    with pytest.raises(NotificationParamException, match="HTTPS is required by config"):
        webhook_notification.send()


def test_send_requires_allowed_host(
    monkeypatch: pytest.MonkeyPatch,
    mock_header_data: HeaderDataType,
) -> None:
    webhook_notification = build_webhook_notification(
        mock_header_data, "https://example.com/webhook"
    )
    enable_webhook_feature(monkeypatch)
    set_webhook_config(
        monkeypatch,
        {
            "ALERT_REPORTS_WEBHOOK_HTTPS_ONLY": True,
            "ALERT_REPORTS_WEBHOOK_ALLOWED_HOSTS": (),
            "ALERT_REPORTS_WEBHOOK_BLOCK_PRIVATE_ADDRESSES": True,
        },
    )
    monkeypatch.setattr(
        "superset.reports.notifications.webhook.requests.post",
        fail_post,
    )

    with pytest.raises(NotificationParamException, match="ALERT_REPORTS_WEBHOOK"):
        webhook_notification.send()


def test_send_rejects_unallowed_host(
    monkeypatch: pytest.MonkeyPatch,
    mock_header_data: HeaderDataType,
) -> None:
    webhook_notification = build_webhook_notification(
        mock_header_data, "https://untrusted.example/webhook"
    )
    enable_webhook_feature(monkeypatch)
    set_webhook_config(
        monkeypatch,
        {
            "ALERT_REPORTS_WEBHOOK_HTTPS_ONLY": True,
            "ALERT_REPORTS_WEBHOOK_ALLOWED_HOSTS": ("trusted.example",),
            "ALERT_REPORTS_WEBHOOK_BLOCK_PRIVATE_ADDRESSES": True,
        },
    )
    monkeypatch.setattr(
        "superset.reports.notifications.webhook.requests.post",
        fail_post,
    )

    with pytest.raises(NotificationParamException, match="not configured"):
        webhook_notification.send()


def test_send_rejects_hostname_that_resolves_private_ip(
    monkeypatch: pytest.MonkeyPatch,
    mock_header_data: HeaderDataType,
) -> None:
    webhook_notification = build_webhook_notification(
        mock_header_data, "https://trusted.example/webhook"
    )
    enable_webhook_feature(monkeypatch)
    set_webhook_config(
        monkeypatch,
        {
            "ALERT_REPORTS_WEBHOOK_HTTPS_ONLY": True,
            "ALERT_REPORTS_WEBHOOK_ALLOWED_HOSTS": ("trusted.example",),
            "ALERT_REPORTS_WEBHOOK_BLOCK_PRIVATE_ADDRESSES": True,
        },
    )
    set_webhook_dns(monkeypatch, ["10.0.0.5"])
    monkeypatch.setattr(
        "superset.reports.notifications.webhook.requests.post",
        fail_post,
    )

    with pytest.raises(NotificationParamException, match="non-public address"):
        webhook_notification.send()


def test_send_rejects_metadata_service_ip(
    monkeypatch: pytest.MonkeyPatch,
    mock_header_data: HeaderDataType,
) -> None:
    webhook_notification = build_webhook_notification(
        mock_header_data, "https://169.254.169.254/latest/meta-data"
    )
    enable_webhook_feature(monkeypatch)
    set_webhook_config(
        monkeypatch,
        {
            "ALERT_REPORTS_WEBHOOK_HTTPS_ONLY": True,
            "ALERT_REPORTS_WEBHOOK_ALLOWED_HOSTS": ("169.254.169.254",),
            "ALERT_REPORTS_WEBHOOK_BLOCK_PRIVATE_ADDRESSES": True,
        },
    )
    set_webhook_dns(monkeypatch, ["169.254.169.254"])
    monkeypatch.setattr(
        "superset.reports.notifications.webhook.requests.post",
        fail_post,
    )

    with pytest.raises(NotificationParamException, match="non-public address"):
        webhook_notification.send()


def test_send_allows_configured_public_host(
    monkeypatch: pytest.MonkeyPatch,
    mock_header_data: HeaderDataType,
) -> None:
    webhook_notification = build_webhook_notification(
        mock_header_data, "https://trusted.example/webhook"
    )
    enable_webhook_feature(monkeypatch)
    set_webhook_config(
        monkeypatch,
        {
            "ALERT_REPORTS_WEBHOOK_HTTPS_ONLY": True,
            "ALERT_REPORTS_WEBHOOK_ALLOWED_HOSTS": ("TRUSTED.EXAMPLE",),
            "ALERT_REPORTS_WEBHOOK_BLOCK_PRIVATE_ADDRESSES": True,
        },
    )
    set_webhook_dns(monkeypatch, ["93.184.216.34"])
    posted_url: list[str] = []
    posted_timeout: list[object] = []

    def post(url: str, **kwargs: object) -> MockResponse:
        posted_url.append(url)
        posted_timeout.append(kwargs["timeout"])
        return MockResponse()

    monkeypatch.setattr(
        "superset.reports.notifications.webhook.requests.post",
        post,
    )

    webhook_notification.send()

    assert posted_url == ["https://trusted.example/webhook"]
    assert posted_timeout == [60]


@pytest.mark.parametrize(
    ("target", "expected_message"),
    [
        ("trusted.example/webhook", "URL is malformed"),
        ("https:///webhook", "URL is malformed"),
        ("https://trusted.example:invalid/webhook", "URL port is malformed"),
    ],
)
def test_send_rejects_malformed_url(
    monkeypatch: pytest.MonkeyPatch,
    mock_header_data: HeaderDataType,
    target: str,
    expected_message: str,
) -> None:
    webhook_notification = build_webhook_notification(mock_header_data, target)
    enable_webhook_feature(monkeypatch)
    set_webhook_config(
        monkeypatch,
        {
            "ALERT_REPORTS_WEBHOOK_HTTPS_ONLY": True,
            "ALERT_REPORTS_WEBHOOK_ALLOWED_HOSTS": ("trusted.example",),
            "ALERT_REPORTS_WEBHOOK_BLOCK_PRIVATE_ADDRESSES": True,
        },
    )
    monkeypatch.setattr(
        "superset.reports.notifications.webhook.requests.post",
        fail_post,
    )

    with pytest.raises(NotificationParamException, match=expected_message):
        webhook_notification.send()


def test_send_rejects_unresolvable_hostname(
    monkeypatch: pytest.MonkeyPatch,
    mock_header_data: HeaderDataType,
) -> None:
    webhook_notification = build_webhook_notification(
        mock_header_data, "https://trusted.example/webhook"
    )
    enable_webhook_feature(monkeypatch)
    set_webhook_config(
        monkeypatch,
        {
            "ALERT_REPORTS_WEBHOOK_HTTPS_ONLY": True,
            "ALERT_REPORTS_WEBHOOK_ALLOWED_HOSTS": ("trusted.example",),
            "ALERT_REPORTS_WEBHOOK_BLOCK_PRIVATE_ADDRESSES": True,
        },
    )
    set_webhook_dns_failure(monkeypatch)
    monkeypatch.setattr(
        "superset.reports.notifications.webhook.requests.post",
        fail_post,
    )

    with pytest.raises(NotificationParamException, match="could not be resolved"):
        webhook_notification.send()


def test_send_rejects_empty_dns_result(
    monkeypatch: pytest.MonkeyPatch,
    mock_header_data: HeaderDataType,
) -> None:
    webhook_notification = build_webhook_notification(
        mock_header_data, "https://trusted.example/webhook"
    )
    enable_webhook_feature(monkeypatch)
    set_webhook_config(
        monkeypatch,
        {
            "ALERT_REPORTS_WEBHOOK_HTTPS_ONLY": True,
            "ALERT_REPORTS_WEBHOOK_ALLOWED_HOSTS": ("trusted.example",),
            "ALERT_REPORTS_WEBHOOK_BLOCK_PRIVATE_ADDRESSES": True,
        },
    )
    set_webhook_dns(monkeypatch, [])
    monkeypatch.setattr(
        "superset.reports.notifications.webhook.requests.post",
        fail_post,
    )

    with pytest.raises(NotificationParamException, match="could not be resolved"):
        webhook_notification.send()


def test_send_allows_configured_host_when_private_address_block_disabled(
    monkeypatch: pytest.MonkeyPatch,
    mock_header_data: HeaderDataType,
) -> None:
    webhook_notification = build_webhook_notification(
        mock_header_data, "http://internal.example./webhook"
    )
    enable_webhook_feature(monkeypatch)
    set_webhook_config(
        monkeypatch,
        {
            "ALERT_REPORTS_WEBHOOK_HTTPS_ONLY": False,
            "ALERT_REPORTS_WEBHOOK_ALLOWED_HOSTS": " INTERNAL.EXAMPLE. ",
            "ALERT_REPORTS_WEBHOOK_BLOCK_PRIVATE_ADDRESSES": False,
        },
    )
    monkeypatch.setattr(
        "superset.reports.notifications.webhook.socket.getaddrinfo",
        lambda *_args, **_kwargs: pytest.fail("DNS lookup should be skipped"),
    )
    posted_url: list[str] = []

    def post(url: str, **_kwargs: object) -> MockResponse:
        posted_url.append(url)
        return MockResponse()

    monkeypatch.setattr(
        "superset.reports.notifications.webhook.requests.post",
        post,
    )

    webhook_notification.send()

    assert posted_url == ["http://internal.example./webhook"]
