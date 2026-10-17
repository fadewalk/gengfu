# 国产大模型兼容性矩阵

> 更夫 AI 链路对各国产大模型 OpenAI 兼容接口的实测结果。
> 检测工具：`scripts/verify_llm_compat.py`（JSON 提取每项跑 3 次）。

## 实测结果

| 模型 | basic | temperature | seed | max_tokens | json_object | json_schema | json_extraction | chinese | 通过 |
|---|---|---|---|---|---|---|---|---|---|
| **DeepSeek / deepseek-chat** | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ | 7/8 |
| **DeepSeek / deepseek-reasoner** | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ | 7/8 |

## 结论与说明

- **DeepSeek 全系可用**：`deepseek-chat`（V3 系）与 `deepseek-reasoner`（R1 系）均为 7/8，唯一失败项
  `json_schema` 是 DeepSeek 服务端未开放该 response_format 模式——**不影响任何更夫功能**，
  代码里 json_schema 仅对 OpenAI 官方域名启用，其余模型走 JSON 围栏提取（实测 3/3 通过）。
- **推理模型已适配**：deepseek-reasoner 的 JSON 输出解析通过，事件报告链的 `<think>` 清理修复已生效
  （此前推理模型在报告场景会解析失败）。
- 更夫设置页的 AI 模型配置（Settings → AI Configuration）填入 DeepSeek base_url `https://api.deepseek.com`
  与 API key 即可直接使用。

## 待实测

| 厂商 | 预设模型 | 状态 |
|---|---|---|
| 智谱 GLM | glm-4.6 / glm-4.5-air / glm-4-flash（免费） | 待 key |
| 阿里 Qwen | qwen-max / qwen-plus / qwen-turbo | 待 key |
| 月之暗面 Kimi | kimi-k2 / moonshot-v1-8k | 待 key |
| 硅基流动（聚合） | DeepSeek-V3 / Qwen2.5-72B | 待 key |

> 复测命令示例：`LLM_API_KEY=sk-xxx python scripts/verify_llm_compat.py --vendor glm`
