# AI 关联引擎设计文档

> 版本: 1.0 | 分支: feature/group-isolation | 日期: 2026-03-30

## 概述

Keep 平台的 AI 关联引擎是一个 LLM 驱动的告警到事件的自动化关联系统。它分析未分配的告警，利用大语言模型理解告警描述的语义相似性、时间接近性、受影响系统和依赖关系，将相关告警智能分组为事件（Incident）。

此功能在商业版 Keep 中需要付费订阅才能使用，我们通过以下改造实现了对开源版本的自助实现。

## 架构

### 整体架构

```
┌─────────────────────────────────────────────────────────┐
│                    Frontend (/ai)                        │
│  ┌──────────┐ ┌───────────┐ ┌──────────────────────┐   │
│  │ StatCard │ │Algorithm  │ │CorrelationResultCard │   │
│  │ Overview │ │Config     │ │ + Trigger Button     │   │
│  └──────────┘ └───────────┘ └──────────────────────┘   │
└────────────────────────┬────────────────────────────────┘
                         │ HTTP
┌────────────────────────▼────────────────────────────────┐
│                   Backend API                            │
│  GET /ai/stats      → 统计 + 算法配置                    │
│  PUT /ai/{id}/settings → 更新算法配置                    │
│  POST /ai/correlate → 手动触发 AI 关联                   │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│               Core Services                             │
│  AISuggestionBl  → LLM 调用（OpenAI 兼容 API）           │
│  IncidentBl      → 事件创建                              │
│  TopologiesService → 拓扑数据（可选）                     │
└─────────────────────────────────────────────────────────┘
```

### 数据流

1. 用户点击"立即关联"按钮
2. 前端调用 `POST /ai/correlate`
3. 后端获取最近 N 条告警（可配置）
4. 可选获取拓扑数据提供上下文
5. 调用 `AISuggestionBl.suggest_incidents()` 发送到 LLM
6. LLM 返回事件建议和置信度分数
7. 过滤低于置信度阈值的建议
8. 自动创建事件（可配置）
9. 记录执行日志
10. 返回关联结果

## 后端实现

### 1. 算法模型定义

**文件**: `keep/api/models/db/ai_external.py`

新增 `internal_ai_correlation` ExternalAI 实例：

```python
internal_ai_correlation = ExternalAI(
    name="LLM Alert Correlation",
    description="""An LLM-powered alert-to-incident correlation engine.
It analyzes unassigned alerts in batch, groups them into incidents based on
description similarity, temporal proximity, affected systems, and service dependencies.
Powered by your configured LLM (OpenAI-compatible API).""",
    version=1,
    api_url=None,   # 不需要外部服务
    api_key=None,   # 使用环境变量 OPENAI_API_KEY
    config_default=json.dumps([...]),
)
```

### 2. 配置项

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| Enabled | bool | true | 启用/禁用 LLM 关联引擎 |
| Max Alerts Per Batch | int | 20 (5-50) | 单次关联运行处理的最大告警数 |
| Confidence Threshold | float | 0.5 (0.0-1.0) | 事件建议的最低置信度分数 |
| Auto Create Incidents | bool | true | 是否自动创建事件 |
| Include Topology Context | bool | false | 是否包含拓扑数据提升关联准确性 |

### 3. API 端点

**文件**: `keep/api/routes/ai.py`

#### GET /ai/stats
返回告警统计和算法配置列表。

#### PUT /ai/{algorithm_id}/settings
更新指定算法的配置项。

#### POST /ai/correlate
手动触发 AI 关联：

```python
def trigger_correlation():
    1. 检查 OPENAI_API_KEY 是否配置
    2. 获取 LLM 算法配置
    3. 解析配置项（max_alerts, confidence_threshold 等）
    4. get_last_alerts(tenant_id, limit=max_alerts) 获取最近告警
    5. convert_db_alerts_to_dto_alerts(alerts) 转换为 DTO
    6. 可选：TopologiesService.get_all_topology_data() 获取拓扑
    7. AISuggestionBl.suggest_incidents() 调用 LLM
    8. 过滤低置信度建议
    9. 自动创建事件（如果启用）
    10. 更新执行日志
    11. 返回 {status, alerts_analyzed, incidents_suggested, ...}
```

### 4. DB 函数改造

**文件**: `keep/api/core/db.py` - `get_or_create_external_ai_settings()`

- 始终创建 internal LLM correlation 配置（不依赖外部服务 URL）
- 仅在 `KEEP_EXTERNAL_AI_TRANSFORMERS_URL` 设置时创建 external Transformers 配置

### 5. LLM 兼容性

支持所有 OpenAI 兼容 API：

```bash
OPENAI_API_KEY=your-api-key
OPENAI_BASE_URL=http://your-llm-endpoint/v1  # 可选
OPENAI_MODEL_NAME=glm-5                       # 可选
```

已测试兼容的模型：
- GLM-5 (智谱)
- Kimi-2.5 (月之暗面)
- MiniMax-2.5
- OpenAI GPT-4o
- 任何 OpenAI 兼容 API

## 前端实现

### 1. 页面结构

**文件**: `keep-ui/app/(keep)/ai/ai-plugins.tsx`

```
AIPlugins (主组件)
├── Header
│   ├── PageTitle + PageSubtitle
│   └── Button "立即关联" (触发关联)
├── Stats Overview (grid 3列)
│   ├── StatCard: 告警总数 (alerts_count)
│   ├── StatCard: 事件总数 (incidents_count)
│   └── StatCard: 首条告警时间 (first_alert_datetime)
├── CorrelationResultCard (关联结果展示)
│   ├── 成功: 4列网格 (已分析/建议/阈值/已创建)
│   └── 无告警: 提示信息
└── Algorithm Config (算法配置面板)
    ├── 算法名称 + 描述 + LLM Badge
    ├── Configuration
    │   ├── bool: checkbox 切换
    │   ├── int/float: range slider + 数值显示
    │   └── 每项带 debounce 保存
    ├── Proposed Settings (如果算法建议新配置)
    └── Execution Logs (最近10条执行日志)
```

### 2. 组件设计

#### StatCard
显示关键指标卡片，带图标、数值和标签。

#### CorrelationResultCard
展示关联运行结果：
- 成功状态：绿色边框 + 4列指标网格
- 无告警状态：灰色边框 + 提示文本

#### RangeInputWithLabel
带数值标签的范围滑块，支持 int 和 float 类型，1秒防抖保存。

### 3. Hooks

**文件**: `keep-ui/utils/hooks/useAI.ts`

```typescript
// 已有
useAIStats()         → GET /ai/stats (SWR, 5秒刷新)
useAIActions()
  .updateAISettings()  → PUT /ai/{id}/settings
  .triggerCorrelation() → POST /ai/correlate (新增)

// 新增类型
CorrelationResult {
  status: string
  message?: string
  alerts_analyzed: number
  incidents_suggested: number
  incidents_above_threshold?: number
  incidents_created: number
}
```

### 4. i18n 支持

**文件**: `keep-ui/i18n/messages/zh-CN.json`

新增约 20 个翻译键（`aiPlugins.*`），包括：
- 页面标题、副标题
- 统计指标标签
- 关联结果描述
- 算法配置标签
- 执行日志相关文本

## 使用方式

### 1. 配置环境变量

```bash
# docker-compose.yml 或 .env
OPENAI_API_KEY=your-private-llm-api-key
OPENAI_BASE_URL=http://your-private-llm-endpoint/v1  # 可选
OPENAI_MODEL_NAME=glm-5                                # 可选
```

### 2. 访问页面

登录后导航到 `/ai`，即可看到：
- 告警和事件统计概览
- LLM Alert Correlation 算法配置
- 执行日志

### 3. 触发关联

点击右上角"立即关联"按钮，系统将：
1. 获取最近 N 条告警
2. 发送到 LLM 分析
3. 展示关联结果（已分析/建议/置信度/已创建事件数）

### 4. 调整配置

在配置面板中可以：
- 启用/禁用引擎
- 调整每批最大告警数（5-50）
- 调整置信度阈值（0.0-1.0）
- 切换自动创建事件
- 切换拓扑上下文

## 与商业版区别

| 功能 | 商业版 | 我们的实现 |
|------|--------|------------|
| 外部 Transformer 服务 | 需要付费 API | 不需要，使用自托管 LLM |
| 自动定时关联 | 定时调度 | 手动触发（可扩展为定时） |
| 拓扑感知关联 | 支持 | 支持（可配置） |
| 置信度过滤 | 支持 | 支持 |
| 自动创建事件 | 支持 | 支持 |
| 算法自学习调参 | 支持 | 支持（proposed settings） |
| 执行日志 | 支持 | 支持 |

## 扩展方向

1. **定时关联**: 添加 APScheduler 定时任务自动运行
2. **实时关联**: 通过 Pusher WebSocket 实时触发
3. **关联历史**: 存储完整的关联历史记录
4. **手动审核模式**: Auto Create = false 时提供审核界面
5. **告警预测**: 基于历史模式预测潜在事件
