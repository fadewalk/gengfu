# AI 多模型配置系统 — 实施计划

## 需求概述

将 AI 模型配置从环境变量方式改为数据库 + UI 界面方式，支持：
- 配置多个 OpenAI 兼容模型（地址 + 密钥 + 模型名）
- 设置首要/次要模型（故障转移）
- 按场景指定使用哪个模型（告警关联、事件报告、RAG、AI 助手）
- 模型连接测试
- 密钥安全存储（SecretManager）
- 管理界面（类似模型应用商店）

## 现状分析

### 当前模型配置方式

仅通过 **一组环境变量** 控制：
```
OPENAI_API_KEY=xxx
OPENAI_BASE_URL=http://endpoint/v1  # 可选
OPENAI_MODEL_NAME=glm-5             # 可选，默认 gpt-4o-2024-08-06
```

### 后端 AI 使用场景（4 个文件）

| 文件 | 场景标识 | 用途 | 客户端创建方式 |
|------|---------|------|---------------|
| `keep/api/bl/ai_suggestion_bl.py:41` | `correlation` | 告警关联/聚类 | `OpenAI(base_url=OPENAI_BASE_URL)` |
| `keep/api/bl/incident_reports.py:85` | `report` | 事件报告生成 | `OpenAI(base_url=OPENAI_BASE_URL)` |
| `keep/api/core/rag.py` | `rag` | 向量搜索/嵌入 | `ChatOpenAI(...)` |
| `keep-ui/app/api/copilotkit/route.ts` | `chat` | 前端 AI 助手 | 直接读 `process.env` |

### 可复用基础设施

| 组件 | 位置 | 说明 |
|------|------|------|
| SecretManager | `keep/secretmanager/` | 密钥安全存储，SMTP 已在用 |
| TenantConfiguration | `keep/api/core/tenant_configuration.py` | 租户配置缓存单例 |
| Settings 路由 | `keep/api/routes/settings.py` | CRUD 模式可参考 |
| AI 设置页面 | `keep-ui/app/(keep)/settings/ai/` | 已存在但功能简陋 |
| SQLModel + Alembic | `keep/api/models/db/` + `migrations/` | 数据库迁移 |

### 核心问题

1. **只支持 1 个模型** — env vars 只有一组值
2. **无法按场景分配** — 所有场景共用同一配置
3. **无故障转移** — 无首要/次要概念
4. **修改需重启** — 环境变量改了要重启容器
5. **密钥不安全** — API Key 明文写在 env/docker-compose 中

---

## 技术方案

### 数据库设计

#### 表 1: `ai_model_config` — 模型端点配置

```sql
CREATE TABLE ai_model_config (
    id              VARCHAR(36) PRIMARY KEY,        -- UUID
    tenant_id       VARCHAR(256) NOT NULL,
    name            VARCHAR(100) NOT NULL,          -- 显示名称，如 "智谱 GLM-4"
    provider        VARCHAR(50)  NOT NULL DEFAULT 'openai_compatible',
    base_url        VARCHAR(500) NOT NULL,          -- API 地址
    api_key_secret  VARCHAR(200) NOT NULL,          -- SecretManager 中的密钥名
    model_name      VARCHAR(100) NOT NULL,          -- 默认模型名
    fallback_models TEXT,                           -- 备选模型列表 JSON: ["glm-3", "gpt-4o-mini"]
    is_default      BOOLEAN      NOT NULL DEFAULT FALSE,
    priority        INT          NOT NULL DEFAULT 0,
    enabled         BOOLEAN      NOT NULL DEFAULT TRUE,
    extra_config    TEXT,                           -- 额外参数 JSON（temperature 等）
    created_by      VARCHAR(256),
    created_at      DATETIME     DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME     DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE(tenant_id, name)
);
```

#### 表 2: `ai_model_assignment` — 场景-模型映射

```sql
CREATE TABLE ai_model_assignment (
    id              VARCHAR(36) PRIMARY KEY,
    tenant_id       VARCHAR(256) NOT NULL,
    scenario        VARCHAR(50)  NOT NULL,  -- correlation | report | rag | chat | suggestion
    model_config_id VARCHAR(36)  NOT NULL,  -- FK -> ai_model_config.id
    priority        INT          NOT NULL DEFAULT 0,
    enabled         BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at      DATETIME     DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME     DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE(tenant_id, scenario, model_config_id),
    FOREIGN KEY (model_config_id) REFERENCES ai_model_config(id) ON DELETE CASCADE
);
```

### 后端架构

#### 新建文件

**`keep/api/models/db/ai_model_config.py`** — SQLModel 数据模型
- `AIModelConfig` — 对应 `ai_model_config` 表
- `AIModelAssignment` — 对应 `ai_model_assignment` 表
- `AIModelConfigDto` — API 请求/响应 DTO
- `AIModelAssignmentDto` — 场景分配 DTO

**`keep/api/bl/ai_model_service.py`** — 统一模型配置服务
- `AIModelConfigService` 类（单例，带缓存）
  - `list_configs(tenant_id)` — 列出所有模型配置
  - `get_config(tenant_id, config_id)` — 获取单个配置
  - `create_config(tenant_id, data)` — 创建配置（密钥存 SecretManager）
  - `update_config(tenant_id, config_id, data)` — 更新配置
  - `delete_config(tenant_id, config_id)` — 删除配置
  - `get_assignments(tenant_id)` — 获取场景分配
  - `update_assignments(tenant_id, assignments)` — 更新场景分配
  - `get_client(tenant_id, scenario)` — 获取指定场景的 OpenAI 客户端（含 fallback）
  - `test_connection(tenant_id, config_id)` — 测试模型连接
- **Fallback 链**：数据库场景分配 → 数据库默认配置 → 环境变量 → 抛出异常

**`keep/api/routes/ai_settings.py`** — API 路由
```
GET    /settings/ai/models              — 列出所有模型配置
POST   /settings/ai/models              — 添加模型配置
PUT    /settings/ai/models/{config_id}  — 更新模型配置
DELETE /settings/ai/models/{config_id}  — 删除模型配置
POST   /settings/ai/models/{config_id}/test  — 测试连接
GET    /settings/ai/assignments         — 获取场景分配
PUT    /settings/ai/assignments         — 更新场景分配
GET    /settings/ai/scenarios           — 获取可用场景列表
```

### 前端设计

#### 重写 `keep-ui/app/(keep)/settings/ai/`

**`ai-settings.tsx`** — 主页面，包含三个 Tab：

**Tab 1: 模型配置（Model Configs）**
- 卡片式列表展示已配置的模型
- 每张卡片显示：名称、提供商、Base URL、模型名、状态（启用/禁用）、是否默认
- 操作按钮：编辑、删除、测试连接、设为默认
- "添加模型" 按钮打开 Modal

**添加/编辑 Modal**:
- 端点名称（必填）
- 提供商选择器（下拉：OpenAI / 智谱 / DeepSeek / 通义千问 / Kimi / 自定义）
- API 地址（必填，提供商选择后自动填充）
- API Key（必填，密码输入框）
- 默认模型名（必填）
- 备选模型列表（可选，逗号分隔）
- 额外参数（可选，JSON 编辑器）
- 设为默认（复选框）
- 测试连接按钮（保存前可先测试）

**Tab 2: 场景分配（Scenario Assignments）**
- 场景列表：告警关联、事件报告、RAG 搜索、AI 助手、通用建议
- 每个场景可选择分配的模型（下拉选择器，支持多选排序）
- 拖拽排序设置优先级
- 保存按钮

**Tab 3: 使用说明**
- 支持的模型列表
- 配置教程
- API 兼容说明

#### 预置模型模板（类似应用商店）

```typescript
const PRESET_MODELS = [
  { provider: 'zhipu', name: '智谱 GLM', base_url: 'https://open.bigmodel.cn/api/paas/v4', models: ['glm-4', 'glm-4-flash', 'glm-3'] },
  { provider: 'deepseek', name: 'DeepSeek', base_url: 'https://api.deepseek.com/v1', models: ['deepseek-chat', 'deepseek-reasoner'] },
  { provider: 'qwen', name: '通义千问', base_url: 'https://dashscope.aliyuncs.com/compatible-mode/v1', models: ['qwen-turbo', 'qwen-plus', 'qwen-max'] },
  { provider: 'moonshot', name: 'Kimi', base_url: 'https://api.moonshot.cn/v1', models: ['moonshot-v1-8k', 'moonshot-v1-32k'] },
  { provider: 'minimax', name: 'MiniMax', base_url: 'https://api.minimax.chat/v1', models: ['MiniMax-Text-01'] },
  { provider: 'openai', name: 'OpenAI', base_url: 'https://api.openai.com/v1', models: ['gpt-4o', 'gpt-4o-mini', 'gpt-4-turbo'] },
  { provider: 'custom', name: '自定义', base_url: '', models: [] },
];
```

用户点击预置模板 → 自动填充 base_url 和 models → 只需输入 API Key 即可。

### 改造现有代码

#### `keep/api/bl/ai_suggestion_bl.py`

```python
# 改造前
from keep.api.consts import OPENAI_BASE_URL, OPENAI_MODEL_NAME
self._client = OpenAI(base_url=OPENAI_BASE_URL) if OPENAI_BASE_URL else OpenAI()

# 改造后
from keep.api.bl.ai_model_service import AIModelConfigService
self._client = AIModelConfigService.get_instance().get_client(
    tenant_id=self.tenant_id,
    scenario="correlation"
)
```

#### `keep/api/bl/incident_reports.py`

```python
# 同上模式，scenario="report"
```

#### `keep/api/core/rag.py`

```python
# 同上模式，scenario="rag"
```

#### `keep-ui/app/api/copilotkit/route.ts`

```typescript
// 改造前：直接读 process.env
// 改造后：调用 /settings/ai/models API 获取 chat 场景的模型配置
```

### Fallback 策略

```
数据库场景分配 → 数据库默认模型 → 环境变量 → 抛出明确异常
```

优先使用数据库配置。如果数据库无配置，降级到环境变量（兼容现有部署方式）。

---

## 实施步骤

### Phase 1: 数据库 & 数据模型
1. 创建 `keep/api/models/db/ai_model_config.py`（SQLModel 模型 + DTO）
2. 在 `keep/api/models/db/__init__.py` 中注册新模型
3. 创建 Alembic migration 脚本
4. 运行 migration 创建新表

**交付物**：数据库表 + 数据模型

### Phase 2: 后端服务层
1. 创建 `keep/api/bl/ai_model_service.py`（统一模型配置服务）
   - CRUD 操作
   - `get_client(tenant_id, scenario)` 方法（含 fallback 链）
   - `test_connection` 方法
   - SecretManager 集成
2. 创建 `keep/api/routes/ai_settings.py`（API 路由）
3. 在主路由中注册新路由

**交付物**：完整后端 API

### Phase 3: 前端 UI
1. 重写 `keep-ui/app/(keep)/settings/ai/ai-settings.tsx`
   - 模型配置管理（卡片列表 + 添加/编辑 Modal）
   - 预置模型模板（应用商店风格）
   - 连接测试功能
2. 新增场景分配 UI
3. 添加 i18n 翻译（zh-CN.json / en.json）

**交付物**：完整前端 UI

### Phase 4: 改造现有代码
1. 改造 `ai_suggestion_bl.py`（scenario="correlation"）
2. 改造 `incident_reports.py`（scenario="report"）
3. 改造 `rag.py`（scenario="rag"）
4. 改造 CopilotKit route（scenario="chat"）
5. 保持 env vars fallback 兼容

**交付物**：所有 AI 功能使用新配置服务

### Phase 5: 测试 & 验证
1. 后端单元测试（AIModelConfigService CRUD + fallback）
2. 后端集成测试（API 路由）
3. 前端手动测试（UI 交互）
4. 端到端测试（配置模型 → AI 功能正常使用）
5. Fallback 测试（无数据库配置时降级到 env vars）

---

## 关键文件清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `keep/api/models/db/ai_model_config.py` | **新建** | SQLModel 数据模型 + DTO |
| `keep/api/bl/ai_model_service.py` | **新建** | 统一模型配置服务 |
| `keep/api/routes/ai_settings.py` | **新建** | API 路由 |
| `keep/api/models/db/__init__.py` | 修改 | 注册新模型 |
| `keep/api/routes/__init__.py` 或主入口 | 修改 | 注册新路由 |
| `migrations/versions/xxx_add_ai_model_config.py` | **新建** | Alembic migration |
| `keep/api/bl/ai_suggestion_bl.py` | 修改 | 改用 AIModelConfigService |
| `keep/api/bl/incident_reports.py` | 修改 | 改用 AIModelConfigService |
| `keep/api/core/rag.py` | 修改 | 改用 AIModelConfigService |
| `keep-ui/app/api/copilotkit/route.ts` | 修改 | 从 API 获取模型配置 |
| `keep-ui/app/(keep)/settings/ai/ai-settings.tsx` | 重写 | 新 UI |
| `keep-ui/app/(keep)/settings/ai/page.tsx` | 修改 | 适配新组件 |
| `keep-ui/messages/zh-CN.json` | 修改 | 添加 i18n |
| `keep-ui/messages/en.json` | 修改 | 添加 i18n |

## 风险评估

| 风险 | 级别 | 缓解措施 |
|------|------|---------|
| 现有部署（env vars）不兼容 | 中 | Fallback 策略：数据库 → env vars |
| API Key 泄露 | 高 | 使用 SecretManager 存储，前端只显示掩码 |
| 多租户隔离 | 中 | 所有查询按 tenant_id 过滤 |
| 数据库迁移失败 | 低 | Alembic 标准流程，支持回滚 |
| CopilotKit 前端改造复杂 | 中 | 渐进式改造，保留 env vars fallback |
| 缓存一致性 | 低 | 参照 TenantConfiguration 的重载机制 |

## 复杂度评估

- **后端**：中等（4-6 小时）— CRUD + 服务层，模式成熟
- **前端**：中等（4-6 小时）— 重写 UI，参考现有设置页模式
- **改造**：低（1-2 小时）— 4 个文件，改动模式统一
- **测试**：低（2-3 小时）
- **总计**：约 11-17 小时

---

## SESSION_ID (for /ccg:execute use)
- CODEX_SESSION: N/A
- GEMINI_SESSION: N/A
