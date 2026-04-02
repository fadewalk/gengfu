---
name: AI 关联引擎功能
description: Keep 平台自实现的 LLM 告警关联引擎，替代商业付费功能
type: project
---

AI 关联引擎（/ai 页面）已完整实现，替代商业版 External AI Transformers。

**核心改动文件：**
- `keep/api/models/db/ai_external.py` — 新增 internal_ai_correlation ExternalAI 算法定义
- `keep/api/core/db.py` — `get_or_create_external_ai_settings()` 改为始终创建 LLM 配置
- `keep/api/routes/ai.py` — 新增 `POST /ai/correlate` 手动触发关联端点
- `keep-ui/app/(keep)/ai/ai-plugins.tsx` — 完整重写为功能仪表盘
- `keep-ui/utils/hooks/useAI.ts` — 新增 triggerCorrelation + CorrelationResult 类型
- `keep-ui/i18n/messages/zh-CN.json` — 新增 ~20 个翻译键

**架构：** 前端 → POST /ai/correlate → AISuggestionBl.suggest_incidents() → LLM API → 自动创建事件

**配置项：** Enabled, Max Alerts Per Batch (5-50), Confidence Threshold (0-1), Auto Create Incidents, Include Topology Context

**LLM 兼容：** 所有 OpenAI 兼容 API（GLM-5, Kimi-2.5, MiniMax, GPT-4o 等），通过 OPENAI_BASE_URL 环境变量配置

**Why:** 用户不想付费使用商业版 AI 功能，基于平台已有的 AISuggestionBl 实现了完整的自托管方案。
**How to apply:** 需要配置 OPENAI_API_KEY 环境变量，可选 OPENAI_BASE_URL 和 OPENAI_MODEL_NAME。设计文档在 `docs/ai-correlation-design.md`。
