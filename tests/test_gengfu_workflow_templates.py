"""
国内场景工作流模板的防回归校验：
- YAML 可解析、结构完整（id/name/description/triggers/actions）
- 引用的 provider 类型真实存在（防止模板指向不存在的 provider 导致安装即失败）
"""

import glob

import yaml

from keep.providers.providers_factory import ProvidersFactory

GENGFU_TEMPLATES = glob.glob("examples/workflows/gengfu-*.yml")


def test_templates_exist():
    assert len(GENGFU_TEMPLATES) >= 3, f"国内模板应至少 3 条，实际 {len(GENGFU_TEMPLATES)}"


def test_templates_parse_and_structure():
    for path in GENGFU_TEMPLATES:
        data = yaml.safe_load(open(path, encoding="utf-8"))
        workflow = data["workflow"]
        for key in ("id", "name", "description", "triggers", "actions"):
            assert key in workflow, f"{path} 缺少 {key}"
        # 中文模板的 name/description 必须是中文（保证模板页展示为中文）
        assert any("\u4e00" <= ch <= "\u9fff" for ch in workflow["name"]), f"{path} name 非中文"


def test_template_provider_types_exist():
    for path in GENGFU_TEMPLATES:
        data = yaml.safe_load(open(path, encoding="utf-8"))
        for action in data["workflow"]["actions"]:
            provider_type = action["provider"]["type"]
            cls = ProvidersFactory.get_provider_class(provider_type)
            assert cls is not None, f"{path} 引用了不存在的 provider: {provider_type}"
