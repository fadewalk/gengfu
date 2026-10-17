#!/usr/bin/env python3
"""
国产大模型 OpenAI 兼容接口验证脚本。

对照更夫（Keep）代码里 AI 调用的真实形态，逐项检测兼容点，输出 Markdown 兼容矩阵。
覆盖代码路径：
- keep/api/bl/ai_suggestion_bl.py   （AI 关联：json_schema 仅对 api.openai.com 启用 + 围栏/think 标签/括号配对兜底解析）
- keep/api/bl/incident_reports.py   （事件报告：```json 围栏正则提取 + json.loads，seed=1239、temperature=0.2 硬编码）

用法（以 DeepSeek 为例）：
    export LLM_API_KEY=sk-xxx
    python scripts/verify_llm_compat.py --vendor deepseek
    python scripts/verify_llm_compat.py --base-url https://api.deepseek.com/v1 \
        --models deepseek-chat deepseek-reasoner --vendor-name DeepSeek

支持 --vendor deepseek|qwen|glm|kimi|siliconflow|ollama，或直接给 --base-url。
结果同时打印 Markdown 表格并写入 --output（默认 llm-compat-results.md）。
"""

import argparse
import json
import os
import re
import time
from dataclasses import dataclass, field

import requests

TIMEOUT = 60
RUNS = 3  # JSON 提取稳定性测试次数

VENDOR_PRESETS = {
    "deepseek": {
        "base_url": "https://api.deepseek.com/v1",
        "models": ["deepseek-chat", "deepseek-reasoner"],
    },
    "qwen": {
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "models": ["qwen3-max", "qwen-plus"],
    },
    "glm": {
        "base_url": "https://open.bigmodel.cn/api/paas/v4",
        # glm-5.3-flash 为最新旗舰；编程套餐订阅 key 仅限 Anthropic 端点，
        # OpenAI 端点付费模型需 API 余额，glm-4-flash 免费可用
        "models": ["glm-5.3-flash", "glm-4-flash"],
    },
    "kimi": {
        "base_url": "https://api.moonshot.cn/v1",
        "models": ["kimi-latest", "kimi-k2-turbo-preview"],
    },
    "siliconflow": {
        "base_url": "https://api.siliconflow.cn/v1",
        "models": ["deepseek-ai/DeepSeek-V3", "Qwen/Qwen2.5-72B-Instruct"],
    },
    "ollama": {
        "base_url": "http://localhost:11434/v1",
        "models": ["qwen2.5:7b"],
        "no_auth": True,
    },
}

# 与 incident_reports.py 一致的围栏提取
FENCE_RE = re.compile(r"```(?:json)?\s*\n(.*?)\n```", re.DOTALL)
# 与 Keep 解析链一致的 think 标签清理（非贪婪，think 内容含大括号也能正确匹配）
THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL)

JSON_PROMPT = (
    "分析以下告警并以 JSON 输出（不要输出其他文字）：\n"
    "告警：CPU 使用率 95%，主机 web-01，环境 production\n"
    'JSON 格式：{"incident_name": "string", "severity": "critical|warning|info", '
    '"summary": "string"}'
)

CHECK_NAMES = [
    "basic", "temperature", "seed", "max_tokens",
    "json_object", "json_schema", "json_extraction", "chinese",
]


@dataclass
class CheckResult:
    name: str
    status: str  # PASS / FAIL
    detail: str = ""


@dataclass
class ModelReport:
    vendor_name: str
    model: str
    checks: list = field(default_factory=list)

    @property
    def passed(self) -> int:
        return sum(1 for c in self.checks if c.status == "PASS")

    def get(self, name: str) -> CheckResult:
        for c in self.checks:
            if c.name == name:
                return c
        return CheckResult(name, "FAIL", "未执行")


def _chat(base_url: str, api_key: str, model: str, messages: list, **params):
    """返回 (content, finish_reason, error)。成功时 error 为 None。"""
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    try:
        resp = requests.post(
            f"{base_url.rstrip('/')}/chat/completions",
            json={"model": model, "messages": messages, **params},
            headers=headers,
            timeout=TIMEOUT,
        )
    except requests.RequestException as e:
        return None, None, f"网络错误: {e}"
    if resp.status_code != 200:
        try:
            msg = resp.json().get("error", {}).get("message", resp.text[:120])
        except Exception:
            msg = resp.text[:120]
        return None, None, f"HTTP {resp.status_code}: {msg}"
    data = resp.json()
    choice = (data.get("choices") or [{}])[0]
    message = choice.get("message") or {}
    return message.get("content"), choice.get("finish_reason"), None


def _simple(base_url, api_key, model, name, **params) -> CheckResult:
    content, finish, error = _chat(
        base_url, api_key, model, [{"role": "user", "content": "回复：ok"}], **params
    )
    if error:
        return CheckResult(name, "FAIL", error)
    if not content:
        return CheckResult(name, "FAIL", f"空 content（finish_reason={finish}）")
    return CheckResult(name, "PASS", f"finish={finish}")


# ---------- 各兼容点检测 ----------


def check_basic(base_url, api_key, model) -> CheckResult:
    return _simple(base_url, api_key, model, "basic")


def check_temperature(base_url, api_key, model) -> CheckResult:
    """Keep 的报告/关联链路固定传 temperature=0.2（可用开关关闭）。"""
    return _simple(base_url, api_key, model, "temperature", temperature=0.2)


def check_seed(base_url, api_key, model) -> CheckResult:
    """事件报告链路固定传 seed=1239。"""
    return _simple(base_url, api_key, model, "seed", seed=1239)


def check_max_tokens(base_url, api_key, model) -> CheckResult:
    """AI 关联链路固定传 max_tokens=4096。"""
    return _simple(base_url, api_key, model, "max_tokens", max_tokens=4096)


def check_json_object(base_url, api_key, model) -> CheckResult:
    content, finish, error = _chat(
        base_url, api_key, model,
        [{"role": "user", "content": JSON_PROMPT}],
        response_format={"type": "json_object"},
    )
    if error:
        return CheckResult("json_object", "FAIL", error)
    try:
        parsed = json.loads(content.strip())
        if not isinstance(parsed, dict) or "incident_name" not in parsed:
            return CheckResult("json_object", "FAIL", "JSON 合法但缺少目标字段")
    except Exception as e:
        return CheckResult("json_object", "FAIL", f"content 非合法 JSON: {e}")
    return CheckResult("json_object", "PASS", f"finish={finish}")


def check_json_schema(base_url, api_key, model) -> CheckResult:
    """Keep 仅对 api.openai.com 启用 json_schema；此处记录各家支持度，为将来放开白名单提供依据。"""
    content, finish, error = _chat(
        base_url, api_key, model,
        [{"role": "user", "content": JSON_PROMPT}],
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "alert_report",
                "schema": {
                    "type": "object",
                    "properties": {
                        "incident_name": {"type": "string"},
                        "severity": {"type": "string"},
                        "summary": {"type": "string"},
                    },
                    "required": ["incident_name", "severity", "summary"],
                },
            },
        },
    )
    if error:
        return CheckResult("json_schema", "FAIL", error)
    return CheckResult("json_schema", "PASS", f"finish={finish}")


def keep_extract_report_style(content: str) -> str:
    """复刻 incident_reports.py 的提取：think 清理 → ```json 围栏正则 → 原文 strip。"""
    content = THINK_RE.sub("", content).strip()
    m = FENCE_RE.search(content)
    return m.group(1).strip() if m else content.strip()


def keep_extract_suggestion_style(content: str) -> str:
    """复刻 ai_suggestion_bl.py 的提取：围栏剥离 → think 清理 → 首个 { 起括号配对。"""
    s = content.strip()
    if s.startswith("```"):
        s = s.split("\n", 1)[1] if "\n" in s else s[3:]
    if s.endswith("```"):
        s = s[:-3].strip()
    s = THINK_RE.sub("", s).strip()
    start = s.find("{")
    if start > 0:
        s = s[start:]
        depth, end = 0, -1
        for i, c in enumerate(s):
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break
        if end > 0:
            s = s[:end]
    return s


def _parses_as_alert_json(content: str, extractor) -> bool:
    try:
        parsed = json.loads(extractor(content))
        return isinstance(parsed, dict) and "incident_name" in parsed
    except Exception:
        return False


def check_json_extraction(base_url, api_key, model) -> CheckResult:
    """跑 RUNS 次，用 Keep 的两条解析链解析无 response_format 的 JSON 输出。"""
    ok_report = ok_suggestion = 0
    has_think = False
    for _ in range(RUNS):
        content, _, error = _chat(base_url, api_key, model, [{"role": "user", "content": JSON_PROMPT}])
        if error:
            return CheckResult("json_extraction", "FAIL", f"基础调用失败: {error}")
        if content and "<think>" in content:
            has_think = True
        if content and _parses_as_alert_json(content, keep_extract_report_style):
            ok_report += 1
        if content and _parses_as_alert_json(content, keep_extract_suggestion_style):
            ok_suggestion += 1
    detail = f"报告链 {ok_report}/{RUNS}，关联链 {ok_suggestion}/{RUNS}"
    if has_think:
        detail += "（输出含 <think> 标签，已由关联链清理）"
    status = "PASS" if ok_report == RUNS and ok_suggestion == RUNS else "FAIL"
    return CheckResult("json_extraction", status, detail)


def check_chinese(base_url, api_key, model) -> CheckResult:
    """Keep 默认 KEEP_DEFAULT_LOCALE=zh_CN，系统提示要求中文输出。"""
    content, _, error = _chat(
        base_url, api_key, model,
        [{"role": "system", "content": "你必须使用简体中文回答。"},
         {"role": "user", "content": "用一句话描述 CPU 使用率过高的风险"}],
    )
    if error:
        return CheckResult("chinese", "FAIL", error)
    if not any("\u4e00" <= ch <= "\u9fff" for ch in (content or "")):
        return CheckResult("chinese", "FAIL", "回复中无中文字符")
    return CheckResult("chinese", "PASS")


CHECKS = [
    check_basic, check_temperature, check_seed, check_max_tokens,
    check_json_object, check_json_schema, check_json_extraction, check_chinese,
]


def verify_model(base_url: str, api_key: str, model: str, vendor_name: str) -> ModelReport:
    report = ModelReport(vendor_name, model)
    for fn in CHECKS:
        try:
            result = fn(base_url, api_key, model)
        except Exception as e:  # 单项异常不中断整个矩阵
            result = CheckResult(fn.__name__.replace("check_", ""), "FAIL", f"脚本异常: {e}")
        report.checks.append(result)
        time.sleep(0.5)  # 温和对待限流
    return report


def render_markdown(reports: list[ModelReport], output_path: str) -> str:
    lines = [
        "# 国产大模型兼容性矩阵",
        "",
        f"> 生成时间：{time.strftime('%Y-%m-%d %H:%M')} · 生成工具：`scripts/verify_llm_compat.py` · JSON 提取每项跑 {RUNS} 次",
        "",
        "| 模型 | " + " | ".join(CHECK_NAMES) + " | 通过 |",
        "|---|" + "---|" * (len(CHECK_NAMES) + 1),
    ]
    for r in reports:
        cells = [{"PASS": "✅", "FAIL": "❌"}.get(r.get(n).status, "❌") for n in CHECK_NAMES]
        lines.append(
            f"| **{r.vendor_name} / {r.model}** | " + " | ".join(cells) + f" | {r.passed}/{len(CHECK_NAMES)} |"
        )
    lines += ["", "## 失败详情", ""]
    fails = [
        f"- **{r.vendor_name}/{r.model}** `{c.name}`：{c.detail}"
        for r in reports for c in r.checks if c.status == "FAIL"
    ]
    lines.extend(fails if fails else ["（无失败项）"])
    text = "\n".join(lines) + "\n"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(text)
    return text


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--vendor", choices=list(VENDOR_PRESETS), help="厂商预设")
    parser.add_argument("--base-url", help="OpenAI 兼容 base_url（覆盖预设）")
    parser.add_argument("--models", nargs="+", help="要测的模型名（覆盖预设）")
    parser.add_argument("--vendor-name", help="矩阵里显示的厂商名（默认取 --vendor）")
    parser.add_argument("--api-key", default="", help="API key，也可用环境变量 LLM_API_KEY")
    parser.add_argument("--output", default="llm-compat-results.md", help="Markdown 结果输出路径")
    parser.add_argument("--list-models", action="store_true", help="只列出端点可用的模型名后退出")
    args = parser.parse_args()

    if args.list_models:
        if not args.base_url and not args.vendor:
            parser.error("必须给 --vendor 或 --base-url")
        preset = VENDOR_PRESETS.get(args.vendor, {})
        base_url = args.base_url or preset["base_url"]
        api_key = args.api_key or os.environ.get("LLM_API_KEY", "")
        headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
        resp = requests.get(f"{base_url.rstrip('/')}/models", headers=headers, timeout=30)
        resp.raise_for_status()
        for m in resp.json().get("data", []):
            print(m.get("id"))
        return

    if not args.vendor and not args.base_url:
        parser.error("必须给 --vendor 或 --base-url")

    preset = VENDOR_PRESETS.get(args.vendor, {})
    base_url = args.base_url or preset["base_url"]
    models = args.models or preset.get("models") or []
    vendor_name = args.vendor_name or args.vendor or base_url
    api_key = args.api_key or os.environ.get("LLM_API_KEY", "")

    if not api_key and not preset.get("no_auth"):
        parser.error("必须给 --api-key 或设置环境变量 LLM_API_KEY（ollama 预设除外）")
    if not models:
        parser.error("必须给 --models（或使用 --vendor 预设的模型清单）")

    reports = []
    for model in models:
        print(f"▶ 测试 {vendor_name} / {model} ...", flush=True)
        reports.append(verify_model(base_url, api_key, model, vendor_name))

    print()
    print(render_markdown(reports, args.output))
    print(f"\n结果已写入 {args.output}")


if __name__ == "__main__":
    main()
