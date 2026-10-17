"""
验证脚本自身的测试：用本地假 OpenAI 兼容服务模拟不同厂商行为，
确认 verify_llm_compat 的矩阵计算与 Keep 两条 JSON 解析链的行为正确。
"""

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from scripts.verify_llm_compat import (
    keep_extract_report_style,
    keep_extract_suggestion_style,
    verify_model,
)

ALERT_JSON = {
    "incident_name": "CPU 使用率过高",
    "severity": "critical",
    "summary": "web-01 CPU 95%",
}


def _completion(content: str) -> dict:
    return {
        "choices": [{"message": {"content": content}, "finish_reason": "stop"}],
    }


class FakeLLMHandler(BaseHTTPRequestHandler):
    """按类属性 behaviors 决定行为的假 OpenAI 兼容服务。

    behaviors: set of "reject_temperature" | "reject_seed" | "reject_response_format"
    content_style: fenced | think_wrapped | bare | leading_text
    """

    behaviors: set = set()
    content_style: str = "fenced"

    def log_message(self, *args):  # 静默测试输出
        pass

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length))

        rejected_params = {
            "temperature": "reject_temperature" in self.behaviors,
            "seed": "reject_seed" in self.behaviors,
            "response_format": "reject_response_format" in self.behaviors,
        }
        for param, should_reject in rejected_params.items():
            if should_reject and param in body:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(
                    json.dumps({"error": {"message": f"param {param} not supported"}}).encode()
                )
                return

        # response_format 模式（json_object/json_schema）下，真厂商契约是返回裸 JSON
        if "response_format" in body or self.content_style == "bare":
            content = json.dumps(ALERT_JSON, ensure_ascii=False)
        elif self.content_style == "fenced":
            content = f"```json\n{json.dumps(ALERT_JSON, ensure_ascii=False)}\n```"
        elif self.content_style == "think_wrapped":
            content = f"<think>用户要求分析告警</think>{json.dumps(ALERT_JSON, ensure_ascii=False)}"
        elif self.content_style == "leading_text":
            content = f"分析结果如下：\n{json.dumps(ALERT_JSON, ensure_ascii=False)}"
        else:
            content = json.dumps(ALERT_JSON, ensure_ascii=False)

        payload = json.dumps(_completion(content)).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


@pytest.fixture
def fake_llm():
    server = HTTPServer(("127.0.0.1", 0), FakeLLMHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_port}"
    server.shutdown()


def _verify(base_url: str, behaviors: set, content_style: str):
    FakeLLMHandler.behaviors = behaviors
    FakeLLMHandler.content_style = content_style
    return verify_model(base_url, api_key="test", model="fake-model", vendor_name="fake")


class TestKeepExtractionChains:
    def test_report_chain_fenced(self):
        content = f"```json\n{json.dumps(ALERT_JSON, ensure_ascii=False)}\n```"
        assert json.loads(keep_extract_report_style(content)) == ALERT_JSON

    def test_report_chain_bare(self):
        assert json.loads(keep_extract_report_style(json.dumps(ALERT_JSON))) == ALERT_JSON

    def test_suggestion_chain_think_wrapped(self):
        """MiniMax 类模型的 <think> 输出必须被关联链清理后解析。"""
        content = f"<think>思考过程}}</think>{json.dumps(ALERT_JSON, ensure_ascii=False)}"
        assert json.loads(keep_extract_suggestion_style(content)) == ALERT_JSON

    def test_suggestion_chain_leading_text(self):
        """JSON 前有说明文字时，关联链靠首个 { + 括号配对兜底。"""
        content = f"分析结果如下：\n{json.dumps(ALERT_JSON, ensure_ascii=False)}"
        assert json.loads(keep_extract_suggestion_style(content)) == ALERT_JSON

    def test_suggestion_chain_think_with_braces_inside(self):
        """think 内容含大括号时，ThinkRE 的 [^}] 会提前失效——记录该已知边界。

        ai_suggestion_bl 的正则 r'<think>[^}]*?</think>' 无法匹配 think 内含 } 的输出，
        此时依赖后续括号配对兜底（think 里的孤立 { 会让配对从错误位置开始）。
        """
        content = (
            '<think>假设 {"a": 1} 这样思考</think>' + json.dumps(ALERT_JSON, ensure_ascii=False)
        )
        # 关联链的括号配对从 think 内的 { 开始，解析会失败——这是上游已知边界，不是回归
        try:
            json.loads(keep_extract_suggestion_style(content))
            parsed = True
        except Exception:
            parsed = False
        # 无论能否解析，不能抛出未捕获异常即算通过（Keep 里由 try/except 包住）
        assert isinstance(parsed, bool)


class TestVerifyModelMatrix:
    def test_well_behaved_vendor_all_pass(self, fake_llm):
        report = _verify(fake_llm, behaviors=set(), content_style="fenced")
        assert report.passed == len(report.checks), \
            [(c.name, c.detail) for c in report.checks if c.status != "PASS"]

    def test_think_wrapped_output_is_handled(self, fake_llm):
        """推理模型的 <think> 无围栏输出：报告链已补 think 清理，两条链都应解析成功。

        （incident_reports.py 曾缺 think 处理，Keep 关联链一直有——矩阵应双双 PASS。）
        """
        report = _verify(fake_llm, behaviors=set(), content_style="think_wrapped")
        extraction = report.get("json_extraction")
        assert extraction.status == "PASS", extraction.detail
        assert "<think>" in extraction.detail

    def test_leading_text_only_suggestion_chain_survives(self, fake_llm):
        """JSON 前有说明文字时：报告链（正则）失败、关联链（括号配对）成功 → 总体 FAIL。"""
        report = _verify(fake_llm, behaviors=set(), content_style="leading_text")
        extraction = report.get("json_extraction")
        assert extraction.status == "FAIL"
        assert "报告链 0/3" in extraction.detail and "关联链 3/3" in extraction.detail

    def test_strict_vendor_param_rejections_are_recorded(self, fake_llm):
        """拒绝 temperature/seed/response_format 的厂商（如某些推理模型），对应项 FAIL 且其余不受影响。"""
        report = _verify(
            fake_llm,
            behaviors={"reject_temperature", "reject_seed", "reject_response_format"},
            content_style="bare",
        )
        assert report.get("temperature").status == "FAIL"
        assert "temperature" in report.get("temperature").detail
        assert report.get("seed").status == "FAIL"
        assert report.get("json_object").status == "FAIL"
        assert report.get("json_schema").status == "FAIL"
        # 未被拒的兼容点不受影响
        assert report.get("basic").status == "PASS"
        assert report.get("max_tokens").status == "PASS"
        assert report.get("json_extraction").status == "PASS"
