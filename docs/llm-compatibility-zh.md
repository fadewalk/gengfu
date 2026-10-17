# 国产大模型兼容性矩阵

> 更夫 AI 链路对各国产大模型 OpenAI 兼容接口的实测结果。
> 检测工具：`scripts/verify_llm_compat.py`（JSON 提取每项跑 3 次）。

## 实测结果

| 模型 | basic | temperature | seed | max_tokens | json_object | json_schema | json_extraction | chinese | 通过 |
|---|---|---|---|---|---|---|---|---|---|
| **DeepSeek / deepseek-chat** | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ | 7/8 |
| **DeepSeek / deepseek-reasoner** | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ | 7/8 |
| **GLM / glm-4-flash**（免费） | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | 8/8 |
| **GLM / glm-5.3-flash** | 429 余额不足（编程套餐订阅 key 仅限 Anthropic 端点） |||||||||
| **GLM / glm-5.3-flash**（经 Anthropic 兼容端点） | ✅ 订阅 key 实测可用，已增强 anthropic provider 支持 base_url |||||||

## 结论与说明

- **DeepSeek 全系可用**：`deepseek-chat`（V3 系）与 `deepseek-reasoner`（R1 系）均为 7/8，唯一失败项
  `json_schema` 是 DeepSeek 服务端未开放该 response_format 模式——**不影响任何更夫功能**，
  代码里 json_schema 仅对 OpenAI 官方域名启用，其余模型走 JSON 围栏提取（实测 3/3 通过）。
- **推理模型已适配**：deepseek-reasoner 的 JSON 输出解析通过，事件报告链的 `<think>` 清理修复已生效
  （此前推理模型在报告场景会解析失败）。
- 更夫设置页的 AI 模型配置（Settings → AI Configuration）填入 DeepSeek base_url `https://api.deepseek.com`
  与 API key 即可直接使用。

## GLM 接入指引（智谱）

- **免费起步**：`glm-4-flash` 在 OpenAI 兼容端点（`https://open.bigmodel.cn/api/paas/v4`）实测 8/8，
  且 **json_schema 原生支持**（比 DeepSeek 更全），零成本接入更夫 AI 链路。
- **最新旗舰 glm-5.3-flash**：编程套餐（Claude Code 套餐）的订阅 key 只能走 Anthropic 兼容端点。
  已增强更夫的 anthropic provider 支持自定义 base_url——工作流里配置
  `base_url=https://open.bigmodel.cn/api/anthropic` + `model=glm-5.3-flash` 即可使用订阅额度（实测通过）。
  AI 分析链路（事件报告/关联）走 OpenAI 协议，5.3 需 API 余额，4-flash 免费。
- anthropic provider 同时修复：推理模型响应首个块是 thinking 导致的取文本崩溃。

## 待实测

| 厂商 | 预设模型 | 状态 |
|---|---|---|
| 智谱 GLM | glm-4.6 / glm-4.5-air / glm-4-flash（免费） | 待 key |
| 阿里 Qwen | qwen-max / qwen-plus / qwen-turbo | 待 key |
| 月之暗面 Kimi | kimi-k2 / moonshot-v1-8k | 待 key |
| 硅基流动（聚合） | DeepSeek-V3 / Qwen2.5-72B | 待 key |

> 复测命令示例：`LLM_API_KEY=sk-xxx python scripts/verify_llm_compat.py --vendor glm`
