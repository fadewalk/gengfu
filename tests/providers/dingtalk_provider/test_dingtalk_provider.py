"""
Tests for the DingTalk provider: signed URL generation, payload building and _notify.
"""

import base64
import hashlib
import hmac
import urllib.parse
from unittest.mock import MagicMock, patch

import pytest

from keep.contextmanager.contextmanager import ContextManager
from keep.exceptions.provider_exception import ProviderException
from keep.providers.dingtalk_provider.dingtalk_provider import (
    DINGTALK_ROBOT_SEND_URL,
    DingtalkProvider,
)
from keep.providers.models.provider_config import ProviderConfig

ACCESS_TOKEN = "test-access-token"
SECRET = "SEC1234567890abcdef"


def _build_provider(**authentication) -> DingtalkProvider:
    config = ProviderConfig(
        description="DingTalk Provider",
        authentication={"access_token": ACCESS_TOKEN, **authentication},
    )
    return DingtalkProvider(
        ContextManager(tenant_id="test"), "dingtalk-test", config
    )


class TestSignedUrl:
    def test_signed_url_contains_timestamp_and_sign(self):
        provider = _build_provider(secret=SECRET)
        ts = 1710000000000
        url = provider._gen_signed_url(ts)

        expected_string_to_sign = f"{ts}\n{SECRET}"
        expected_sign = urllib.parse.quote_plus(
            base64.b64encode(
                hmac.new(
                    SECRET.encode(),
                    expected_string_to_sign.encode(),
                    digestmod=hashlib.sha256,
                ).digest()
            )
        )
        assert url.startswith(
            f"{DINGTALK_ROBOT_SEND_URL}?access_token={ACCESS_TOKEN}&timestamp={ts}&sign="
        )
        assert url.endswith(f"sign={expected_sign}")

    def test_signed_url_sign_is_verifiable(self):
        provider = _build_provider(secret=SECRET)
        ts = 1710000000001
        url = provider._gen_signed_url(ts)
        sign = url.split("sign=")[1]
        decoded = base64.b64decode(urllib.parse.unquote_plus(sign))
        recomputed = hmac.new(
            SECRET.encode(), f"{ts}\n{SECRET}".encode(), hashlib.sha256
        ).digest()
        assert decoded == recomputed


class TestMarkdownPayload:
    def test_basic_payload(self):
        payload = DingtalkProvider._build_markdown_payload("hello", "title")
        assert payload["msgtype"] == "markdown"
        assert payload["markdown"] == {"title": "title", "text": "hello"}
        assert payload["at"]["isAtAll"] is False

    def test_at_mobiles_and_at_all(self):
        payload = DingtalkProvider._build_markdown_payload(
            "hello", "title", at_mobiles=["13800138000"], at_all=True
        )
        assert payload["at"] == {"isAtAll": True, "atMobiles": ["13800138000"]}


class TestNotify:
    def test_notify_success(self):
        provider = _build_provider()
        response = MagicMock()
        response.json.return_value = {"errcode": 0, "errmsg": "ok"}
        response.raise_for_status.return_value = None
        with patch("requests.post", return_value=response) as mock_post:
            result = provider._notify(message="hello", title="CPU 告警")

        assert result == {"errcode": 0, "errmsg": "ok"}
        url = mock_post.call_args[0][0]
        assert f"access_token={ACCESS_TOKEN}" in url
        assert mock_post.call_args[1]["json"]["markdown"]["text"] == "hello"

    def test_notify_with_secret_appends_signature_params(self):
        provider = _build_provider(secret=SECRET)
        response = MagicMock()
        response.json.return_value = {"errcode": 0, "errmsg": "ok"}
        response.raise_for_status.return_value = None
        with patch("requests.post", return_value=response) as mock_post:
            provider._notify(message="hello")

        url = mock_post.call_args[0][0]
        assert "timestamp=" in url and "sign=" in url

    def test_notify_empty_message_raises(self):
        provider = _build_provider()
        with pytest.raises(ProviderException):
            provider._notify(message="")

    def test_notify_nonzero_errcode_raises(self):
        provider = _build_provider()
        response = MagicMock()
        response.json.return_value = {
            "errcode": 310000,
            "errmsg": "keywords not in content",
        }
        response.raise_for_status.return_value = None
        with patch("requests.post", return_value=response):
            with pytest.raises(ProviderException) as exc_info:
                provider._notify(message="hello")
        assert "310000" in str(exc_info.value)
