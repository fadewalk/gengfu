"""
Tests for the WeCom provider: payload building and _notify.
"""

from unittest.mock import MagicMock, patch

import pytest

from keep.contextmanager.contextmanager import ContextManager
from keep.exceptions.provider_exception import ProviderException
from keep.providers.models.provider_config import ProviderConfig
from keep.providers.wecom_provider.wecom_provider import (
    WECOM_ROBOT_SEND_URL,
    WecomProvider,
)

KEY = "test-webhook-key"


def _build_provider() -> WecomProvider:
    config = ProviderConfig(description="WeCom Provider", authentication={"key": KEY})
    return WecomProvider(ContextManager(tenant_id="test"), "wecom-test", config)


class TestPayloads:
    def test_markdown_payload(self):
        payload = WecomProvider._build_markdown_payload("hello")
        assert payload == {"msgtype": "markdown", "markdown": {"content": "hello"}}

    def test_text_payload_with_at_all(self):
        payload = WecomProvider._build_text_payload("hello", at_all=True)
        assert payload["text"]["mentioned_mobile_list"] == ["@all"]

    def test_text_payload_with_mobiles(self):
        payload = WecomProvider._build_text_payload(
            "hello", mentioned_mobiles=["13800138000"]
        )
        assert payload["text"]["mentioned_mobile_list"] == ["13800138000"]

    def test_text_payload_without_at_has_no_mention_key(self):
        payload = WecomProvider._build_text_payload("hello")
        assert "mentioned_mobile_list" not in payload["text"]


class TestNotify:
    def test_notify_markdown_includes_title_as_heading(self):
        provider = _build_provider()
        response = MagicMock()
        response.json.return_value = {"errcode": 0, "errmsg": "ok"}
        response.raise_for_status.return_value = None
        with patch("requests.post", return_value=response) as mock_post:
            provider._notify(message="hello", title="CPU 告警")

        url = mock_post.call_args[0][0]
        assert url == f"{WECOM_ROBOT_SEND_URL}?key={KEY}"
        sent = mock_post.call_args[1]["json"]
        assert sent["msgtype"] == "markdown"
        assert sent["markdown"]["content"].startswith("## CPU 告警")

    def test_notify_with_at_downgrades_to_text(self):
        provider = _build_provider()
        response = MagicMock()
        response.json.return_value = {"errcode": 0, "errmsg": "ok"}
        response.raise_for_status.return_value = None
        with patch("requests.post", return_value=response) as mock_post:
            provider._notify(message="hello", at_mobiles=["13800138000"])

        sent = mock_post.call_args[1]["json"]
        assert sent["msgtype"] == "text"
        assert sent["text"]["mentioned_mobile_list"] == ["13800138000"]

    def test_notify_with_link_appends_markdown_link(self):
        provider = _build_provider()
        response = MagicMock()
        response.json.return_value = {"errcode": 0, "errmsg": "ok"}
        response.raise_for_status.return_value = None
        with patch("requests.post", return_value=response) as mock_post:
            provider._notify(message="hello", link_url="http://gengfu/alerts/fp1")
        sent = mock_post.call_args[1]["json"]
        assert "[查看详情](http://gengfu/alerts/fp1)" in sent["markdown"]["content"]

    def test_notify_empty_message_raises(self):
        provider = _build_provider()
        with pytest.raises(ProviderException):
            provider._notify(message="")

    def test_notify_nonzero_errcode_raises(self):
        provider = _build_provider()
        response = MagicMock()
        response.json.return_value = {"errcode": 93000, "errmsg": "invalid webhook"}
        response.raise_for_status.return_value = None
        with patch("requests.post", return_value=response):
            with pytest.raises(ProviderException) as exc_info:
                provider._notify(message="hello")
        assert "93000" in str(exc_info.value)
