"""
Tests for the Anthropic provider: base_url passthrough and thinking-block-safe text extraction.

背景：GLM-5.x / Claude thinking 等推理模型的响应里首个 content 块是 thinking（无 .text），
原实现 response.content[0].text 会直接 AttributeError；base_url 字段用于接入
国产厂商的 Anthropic 兼容端点（GLM / Kimi 编程套餐 key）。
"""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from keep.contextmanager.contextmanager import ContextManager
from keep.providers.anthropic_provider.anthropic_provider import AnthropicProvider
from keep.providers.models.provider_config import ProviderConfig


def _build_provider(**authentication) -> AnthropicProvider:
    config = ProviderConfig(
        description="Anthropic Provider",
        authentication={"api_key": "test-key", **authentication},
    )
    return AnthropicProvider(
        ContextManager(tenant_id="test"), "anthropic-test", config
    )


def _response_with_blocks(*blocks) -> SimpleNamespace:
    """构造 anthropic SDK 风格的响应对象。"""
    return SimpleNamespace(content=list(blocks))


class TestBaseUrl:
    def test_base_url_passed_to_client(self):
        provider = _build_provider(
            base_url="https://open.bigmodel.cn/api/anthropic",
            model="glm-5.3-flash",
        )
        with patch(
            "keep.providers.anthropic_provider.anthropic_provider.Anthropic"
        ) as mock_client_cls:
            mock_client_cls.return_value.messages.create.return_value = (
                _response_with_blocks(SimpleNamespace(type="text", text="ok"))
            )
            provider._query(prompt="ping")

        _, kwargs = mock_client_cls.call_args
        assert kwargs["base_url"] == "https://open.bigmodel.cn/api/anthropic"
        assert kwargs["api_key"] == "test-key"

    def test_no_base_url_defaults_to_official(self):
        provider = _build_provider()
        with patch(
            "keep.providers.anthropic_provider.anthropic_provider.Anthropic"
        ) as mock_client_cls:
            mock_client_cls.return_value.messages.create.return_value = (
                _response_with_blocks(SimpleNamespace(type="text", text="ok"))
            )
            provider._query(prompt="ping")

        _, kwargs = mock_client_cls.call_args
        assert "base_url" not in kwargs


class TestTextExtraction:
    def _query_with_blocks(self, provider, *blocks):
        with patch(
            "keep.providers.anthropic_provider.anthropic_provider.Anthropic"
        ) as mock_client_cls:
            mock_client_cls.return_value.messages.create.return_value = (
                _response_with_blocks(*blocks)
            )
            return provider._query(prompt="ping")

    def test_thinking_block_then_text_block(self):
        """GLM-5.x 实测返回 [thinking, text] 两个块，必须取到 text 块。"""
        provider = _build_provider()
        result = self._query_with_blocks(
            provider,
            SimpleNamespace(type="thinking", thinking="let me think"),
            SimpleNamespace(type="text", text='{"answer": "ok"}'),
        )
        assert result["response"] == {"answer": "ok"}

    def test_text_only_block(self):
        provider = _build_provider()
        result = self._query_with_blocks(
            provider, SimpleNamespace(type="text", text="plain answer")
        )
        assert result["response"] == "plain answer"

    def test_no_text_block_raises_with_block_types(self):
        provider = _build_provider()
        with pytest.raises(ValueError) as exc_info:
            self._query_with_blocks(
                provider, SimpleNamespace(type="thinking", thinking="only thinking")
            )
        assert "thinking" in str(exc_info.value)
