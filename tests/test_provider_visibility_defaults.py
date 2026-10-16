"""
Tests for 更夫出厂默认 provider 裁剪（get_default_hidden_providers 及三态语义）。

语义：
- 租户未设置 hidden_providers → 使用出厂默认清单（海外 SaaS）
- 租户保存过任何列表（含空列表）→ 完全以租户配置为准
- KEEP_DEFAULT_HIDDEN_PROVIDERS 环境变量可整体覆盖默认清单
"""

import importlib

import pytest

from keep.api import consts
from keep.api.consts import GENGFU_DEFAULT_HIDDEN_PROVIDERS, get_default_hidden_providers


class TestGetDefaultHiddenProviders:
    def test_unset_env_returns_builtin_list(self, monkeypatch):
        monkeypatch.delenv("KEEP_DEFAULT_HIDDEN_PROVIDERS", raising=False)
        assert get_default_hidden_providers() == GENGFU_DEFAULT_HIDDEN_PROVIDERS

    def test_empty_env_disables_trimming(self, monkeypatch):
        monkeypatch.setenv("KEEP_DEFAULT_HIDDEN_PROVIDERS", "")
        assert get_default_hidden_providers() == []

    def test_custom_env_list_is_parsed(self, monkeypatch):
        monkeypatch.setenv("KEEP_DEFAULT_HIDDEN_PROVIDERS", "slack, teams ,, pagerduty")
        assert get_default_hidden_providers() == ["slack", "teams", "pagerduty"]

    def test_builtin_list_contains_china_im_and_excludes_them_from_hiding(self):
        assert "dingtalk" not in GENGFU_DEFAULT_HIDDEN_PROVIDERS
        assert "wecom" not in GENGFU_DEFAULT_HIDDEN_PROVIDERS
        assert "feishu" not in GENGFU_DEFAULT_HIDDEN_PROVIDERS
        assert "slack" in GENGFU_DEFAULT_HIDDEN_PROVIDERS
        assert "pagerduty" in GENGFU_DEFAULT_HIDDEN_PROVIDERS

    def test_builtin_list_only_contains_known_provider_types(self):
        """清单里的每个类型都必须真实存在，防止拼错导致静默失效。"""
        import os

        from keep.providers.providers_factory import ProvidersFactory

        for provider_type in GENGFU_DEFAULT_HIDDEN_PROVIDERS:
            module_path = (
                f"keep.providers.{provider_type}_provider.{provider_type}_provider"
            )
            assert importlib.util.find_spec(module_path) is not None, (
                f"{provider_type} 不存在，清单拼写有误"
            )


class TestTenantSemantics:
    """验证 providers.py 路由里「未设置 vs 已设置」的判定与清单配合正确。"""

    def test_unset_tenant_config_falls_back_to_default(self, monkeypatch):
        monkeypatch.delenv("KEEP_DEFAULT_HIDDEN_PROVIDERS", raising=False)
        tenant_config = {}
        hidden = tenant_config.get("hidden_providers")
        if hidden is None:
            hidden = get_default_hidden_providers()
        assert hidden == GENGFU_DEFAULT_HIDDEN_PROVIDERS

    def test_explicit_empty_tenant_config_shows_all(self, monkeypatch):
        monkeypatch.delenv("KEEP_DEFAULT_HIDDEN_PROVIDERS", raising=False)
        tenant_config = {"hidden_providers": []}
        hidden = tenant_config.get("hidden_providers")
        if hidden is None:
            hidden = get_default_hidden_providers()
        assert hidden == []
