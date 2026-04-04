# AI 关联引擎设计文档

> 版本: 1.1 | 分支: feature/group-isolation | 日期: 2026-03-31

## 一、背景

Keep 商业版通过 External AI Transformers 服务（需付费订阅）提供告警到事件的自动关联能力。开源版缺少此功能，我们实现了基于自托管 LLM 的 AI 关联引擎作为替代方案。

**核心需求**：利用 OpenAI 兼容 API（支持 GLM、Kimi、MiniMax 等国产模型）分析未分配告警，自动将语义相关、时间接近、受影响系统关联的告警分组为事件（Incident）。

## 二、方案选型

| 方案 | 优点 | 缺点 | 结论 |
|------|------|------|------|
| 直接调用 External AI Transformers 服务 | 与商业版一致 | 需要外部付费服务，不支持国产 LLM | 不选 |
| 自托管 Transformers + 本地推理 | 数据不出域 | 模型部署成本高，推理质量低 | 不选 |
| **OpenAI 兼容 API + Prompt Engineering** | 支持任意 LLM，成本低，灵活 | 需要处理不同 LLM 返回格式差异 | **选定** |

选定方案的关键决策：通过 JSON Schema 约束 LLM 输出 + FIELD_MAP 兼容层适配不同模型的字段命名差异。

## 三、影响范围

### 后端

| 文件 | 类型 | 说明 |
|------|------|------|
| `keep/api/bl/ai_suggestion_bl.py` | 修改 | 核心逻辑：LLM 调用、字段归一化、告警名解析 |
| `keep/api/routes/ai.py` | 修改 | 新增 `POST /ai/correlate` 端点 |
| `keep/api/models/incident.py` | 修改 | `IncidentCandidate` 模型增加容错 |
| `keep/api/models/ai_external.py` | 修改 | JSON 序列化兼容 |
| `keep/api/core/db.py` | 修改 | AI 设置双序列化修复 |
| `keep/api/models/db/ai_external.py` | 修改 | `internal_ai_correlation` 算法定义 |

### 前端

| 文件 | 类型 | 说明 |
|------|------|------|
| `keep-ui/app/(keep)/ai/ai-plugins.tsx` | 修改 | 关联按钮、结果卡片、算法配置面板 |
| `keep-ui/utils/hooks/useAI.ts` | 修改 | 新增 `triggerCorrelation()` |
| `keep-ui/middleware.ts` | 修改 | `/backend/` 代理在 NOAUTH 模式下生效 |
| `keep-ui/i18n/messages/zh-CN.json` | 修改 | 约 20 个翻译键 |

### 数据库

无新增表。复用现有 `external_ai` 表存储 `internal_ai_correlation` 算法配置。

## 四、架构设计

### 数据流

```
用户点击"立即关联"
       │
       ▼
POST /ai/correlate
       │
       ├── 1. 获取最近 N 条告警 (可配置, 默认 20)
       ├── 2. 可选：获取拓扑数据 (Topology Context)
       ├── 3. 构建 Prompt → 发送到 LLM
       ├── 4. 解析 LLM 响应（FIELD_MAP 字段归一化）
       ├── 5. 告警名称 → 索引解析
       ├── 6. 过滤低置信度建议
       └── 7. 自动创建事件（可配置）
              │
              ▼
       返回关联结果（已分析/建议/已创建）
```

### LLM 响应归一化（FIELD_MAP）

不同 LLM 返回的 JSON 字段名不同，通过 FIELD_MAP 统一映射：

```python
FIELD_MAP = {
    # incident_name 变体
    "title": "incident_name", "name": "incident_name",
    "incident_title": "incident_name", "incident_id": "incident_name",
    # alerts 变体
    "included_alerts": "alerts", "alert_indices": "alerts",
    "alert_ids": "alerts", "grouped_alert_ids": "alerts",
    "alert_names": "alerts", "involved_alerts": "alerts",
    # reasoning 变体
    "root_cause_hypothesis": "reasoning", "root_cause": "reasoning",
    "description": "reasoning", "analysis": "reasoning",
    "potential_root_cause": "reasoning", "issue": "reasoning",
    # recommended_actions 变体
    "recommendations": "recommended_actions", "actions": "recommended_actions",
    "suggested_actions": "recommended_actions", "initial_actions": "recommended_actions",
    # ... 更多映射
}
```

### 告警名称解析

GLM 等模型可能返回告警名称字符串（如 `["HighDiskUsage", "HighCPU"]`）而非 1-based 索引。处理流程：

1. 构建 `alert_name_to_index` 查找表（name → 1-based index）
2. 尝试精确匹配 → 大小写不敏感匹配 → 带 `Alert N:` 前缀剥离匹配
3. 未匹配的记录 warning 日志

### Pydantic 模型容错

`IncidentCandidate` 做了以下调整以适配各种 LLM 输出：

- `alerts: List[Any]`（接受 int 和 string）
- 所有字段设置默认值（LLM 可能返回不完整数据）
- `Extra.allow` 允许额外字段
- `coerce_alerts` validator 自动转换 string → int

## 五、配置项

| 配置项 | 类型 | 默认值 | 范围 | 说明 |
|--------|------|--------|------|------|
| Enabled | bool | true | - | 启用/禁用引擎 |
| Max Alerts Per Batch | int | 20 | 5-50 | 单次处理告警数 |
| Confidence Threshold | float | 0.5 | 0.0-1.0 | 最低置信度 |
| Auto Create Incidents | bool | true | - | 是否自动创建事件 |
| Include Topology Context | bool | false | - | 是否包含拓扑数据 |

### 环境变量

```bash
OPENAI_API_KEY=your-api-key           # 必填
OPENAI_BASE_URL=http://endpoint/v1    # 可选，默认 OpenAI
OPENAI_MODEL_NAME=glm-5               # 可选，默认 gpt-4o
```

已测试兼容的模型：GLM-5/GLM-5.1（智谱）、Kimi-2.5（月之暗面）、MiniMax-2.5、GPT-4o

## 六、已修复的问题

### 1. `logger` NameError
`_process_incidents()` 中 `logger` 应为 `self.logger`，导致未绑定告警处理时抛 NameError。

### 2. GLM 字段名不匹配
GLM 返回 `involved_alerts`、`issue_type`、`initial_actions` 等非标准字段名，Pydantic 校验失败。通过扩展 FIELD_MAP 覆盖。

### 3. 告警名称 vs 索引
GLM 返回告警名称字符串而非整数索引。新增 `alert_name_to_index` 查找表 + `isinstance(i, int)` 类型守卫。

### 4. AI 设置双序列化
`update_external_ai_settings()` 对 JSON 列执行了 `json.dumps()`，导致存储了双重转义的字符串。修复为 Column(JSON) 直接接受 Python 对象。

### 5. middleware `/backend/` 代理
NOAUTH 模式下 `/backend/` 代理重写被跳过（在 auth check 之后）。将重写逻辑移到 auth check 之前。

## 七、验收标准

- [x] `/ai` 页面展示告警统计和算法配置
- [x] 点击"立即关联"触发 LLM 分析
- [x] GLM-5.1 返回的结果被正确解析为事件
- [x] 非标准字段名被 FIELD_MAP 自动归一化
- [x] 告警名称字符串被解析为正确的索引
- [x] 置信度低于阈值的建议被过滤
- [x] 高置信度建议自动创建为事件
- [x] 执行日志被记录并可查看
- [x] 算法配置可通过 UI 调整并持久化

## 八、扩展方向

1. **定时关联**：添加 APScheduler 定时任务自动运行
2. **实时关联**：通过 Pusher WebSocket 实时触发
3. **关联历史**：存储完整的关联历史记录
4. **手动审核模式**：Auto Create = false 时提供审核界面
5. **告警预测**：基于历史模式预测潜在事件
6. **组级隔离**：关联引擎支持按 group_id 过滤告警范围
