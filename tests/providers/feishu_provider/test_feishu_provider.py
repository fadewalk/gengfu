"""
Tests for the Feishu provider: sign generation, card payload and _notify.
"""

import base64
import hashlib
import hmac
from unittest.mock import MagicMock, patch

import pytest

from keep.contextmanager.contextmanager import ContextManager
from keep.exceptions.provider_exception import ProviderException
from keep.providers.feishu_provider.feishu_provider import (
    FEISHU_ROBOT_SEND_URL,
    FeishuProvider,
)
from keep.providers.models.provider_config import ProviderConfig

HOOK_TOKEN = "test-hook-token"
SECRET = "SECtestsecret"


def _build_provider(**authentication) -> FeishuProvider:
    config = ProviderConfig(
        description="Feishu Provider",
        authentication={"hook_token": HOOK_TOKEN, **authentication},
    )
    return FeishuProvider(ContextManager(tenant_id="test"), "feishu-test", config)


class TestSign:
    def test_sign_is_verifiable(self):
        """飞书签名：把 f"{timestamp}\\n{secret}" 作为 HMAC key，消息为空。"""
        ts = 1710000000
        sign = FeishuProvider._gen_sign(ts, SECRET)
        expected = hmac.new(
            f"{ts}\n{SECRET}".encode("utf-8"), digestmod=hashlib.sha256
        ).digest()
        assert base64.b64decode(sign) == expected

    def test_sign_differs_per_timestamp(self):
        assert FeishuProvider._gen_sign(1710000000, SECRET) != FeishuProvider._gen_sign(
            1710000001, SECRET
        )


class TestCardPayload:
    def test_basic_card(self):
        payload = FeishuProvider._build_card_payload("hello", "CPU 告警")
        assert payload["msg_type"] == "interactive"
        assert payload["card"]["header"]["title"]["content"] == "CPU 告警"
        assert payload["card"]["header"]["template"] == "blue"
        assert payload["card"]["elements"][0]["content"] == "hello"

    def test_at_all_prepends_mention(self):
        payload = FeishuProvider._build_card_payload("hello", "t", at_all=True)
        assert payload["card"]["elements"][0]["content"].startswith("<at id=all></at>")

    def test_link_url_adds_action_button(self):
        payload = FeishuProvider._build_card_payload(
            "hello", "t", link_url="http://gengfu/incidents/1"
        )
        action = payload["card"]["elements"][-1]
        assert action["tag"] == "action"
        assert action["actions"][0]["url"] == "http://gengfu/incidents/1"
        assert action["actions"][0]["text"]["content"] == "查看详情"

    def test_invalid_color_falls_back_to_blue(self):
        payload = FeishuProvider._build_card_payload("hello", "t", color="rainbow")
        assert payload["card"]["header"]["template"] == "blue"


class TestNotify:
    def test_notify_success_without_secret(self):
        provider = _build_provider()
        response = MagicMock()
        response.json.return_value = {"code": 0, "msg": "success"}
        response.raise_for_status.return_value = None
        with patch("requests.post", return_value=response) as mock_post:
            result = provider._notify(message="hello", title="告警")

        assert result == {"code": 0, "msg": "success"}
        url = mock_post.call_args[0][0]
        assert url == f"{FEISHU_ROBOT_SEND_URL}/{HOOK_TOKEN}"
        sent = mock_post.call_args[1]["json"]
        assert "timestamp" not in sent and "sign" not in sent

    def test_notify_with_secret_appends_sign_fields(self):
        provider = _build_provider(secret=SECRET)
        response = MagicMock()
        response.json.return_value = {"code": 0, "msg": "success"}
        response.raise_for_status.return_value = None
        with patch("requests.post", return_value=response) as mock_post:
            provider._notify(message="hello")

        sent = mock_post.call_args[1]["json"]
        assert "timestamp" in sent and "sign" in sent

    def test_notify_empty_message_raises(self):
        provider = _build_provider()
        with pytest.raises(ProviderException):
            provider._notify(message="")

    def test_notify_nonzero_code_raises(self):
        provider = _build_provider()
        response = MagicMock()
        response.json.return_value = {"code": 19021, "msg": "sign match fail"}
        response.raise_for_status.return_value = None
        with patch("requests.post", return_value=response):
            with pytest.raises(ProviderException) as exc_info:
                provider._notify(message="hello")
        assert "19021" in str(exc_info.value)

    def test_notify_legacy_status_code_response_is_supported(self):
        provider = _build_provider()
        response = MagicMock()
        response.json.return_value = {"StatusCode": 0, "StatusMessage": "success"}
        response.raise_for_status.return_value = None
        with patch("requests.post", return_value=response):
            provider._notify(message="hello")
