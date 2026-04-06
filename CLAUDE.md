# Keep 项目约定

## 技术栈
- 前端：Next.js + TypeScript（`keep-ui/`）
- 后端：FastAPI + Python（`keep/api/`）
- 数据库：MySQL（SQLAlchemy ORM）

## 本地开发
- 前后端分离开发：前端 `keep-ui/` 独立启动，后端通过 docker-compose 运行
- 环境变量参考 `docker-compose.common.yml`

## 分支策略
- `main` — 上游主分支，只同步不推送
- `develop` / `feature/*` — 本地开发分支（不推送上游）
- 所有改动在 develop 或 feature 分支上做

## Remote 仓库
- **origin** — GitHub 个人仓库 (https://github.com/fadewalk/keep)
- **gitee** — Gitee 个人仓库 (https://gitee.com/wyule/keep)
- **upstream** — 官方仓库 (https://github.com/keephq/keep)

## 版本锁定
- **@monaco-editor/react**: 锁定在 `4.7.0-rc.0`（不要升级到 `4.8.x`）。`4.8.x` 的 worker 初始化存在破坏性变更，会导致 Docker 环境中的 hydration 错误。未经完整 Docker 环境测试，不要升级此包。

## UI 质量要求
- 避免明显的 AI 模板风格（紫色渐变、emoji 图标、仅默认字体）
- 优先使用真实截图、可信模块和任务流程，而非装饰性视觉元素
- UI 实现前先定义排版系统、设计令牌、页面层级和组件状态

## 本地启动

### 后端（Docker）
```bash
docker compose up -d
# 或独立容器模式参考 docker-compose.common.yml
```

### 前端（本地，保留汉化修改）
```bash
cd keep-ui && pnpm install && node scripts/build-monaco-workers-turbopack.js
nohup npx next dev -p 3000 > /tmp/keep-frontend.log 2>&1 &
```

### 停止服务
```bash
docker compose down
kill $(lsof -ti :3000)
```

## i18n 汉化
- 前端使用 `next-intl`，翻译文件: `keep-ui/messages/zh-CN.json` 和 `en.json`
- 后端使用 `keep/api/i18n/`（`translator.py` 提供 `t()` 和 `tr()` 函数）
- 不要用 `--turbopack`：与 Next.js 内置 Google Fonts 不兼容
- 不要用 docker-compose.dev.yml 启动前端：会覆盖本地汉化代码

## 设计文档
- 完成需求设计后，写设计文档到项目 `wiki/` 目录（不放 `docs/`，那是技术文档站）
- 命名格式：`YYMMDD-HHMMSS-文档名称.md`，如 `260402-200535-AI模型配置管理设计.md`
- 内容至少包含：背景、方案选型、影响范围、验收标准

## 工作流程
- 完成设计、需求实现或 bug 修复后，**主动提交 git** 并**更新 wiki 文档**
- **不需要用户提醒提交**，完成后自动执行 git add/commit
- 提交信息要求：简洁说明改动内容（功能/修复/优化），避免无意义描述
- commit 格式参考：`fix: 描述`、`feat: 描述`、`refactor: 描述`、`docs: 描述`

## 编译与重启

修改代码后需要重新构建 Docker 镜像并重启容器才能生效。项目使用 `deploy/idc/docker-compose.yml` 编排。

### 后端改动（Python）
```bash
cd deploy/idc && docker compose build keep-backend && docker compose up -d keep-backend
```

### 前端改动（TypeScript/Next.js）
```bash
cd deploy/idc && docker compose build keep-frontend && docker compose up -d keep-frontend
```
注意：前端构建较慢（约 5-10 分钟），因为包含 Next.js 全量 build。

### 前后端都改了
```bash
cd deploy/idc && docker compose build keep-backend keep-frontend && docker compose up -d
```

### 常见问题
- 端口冲突（`port already allocated`）：先 `docker stop <旧容器名> && docker rm <旧容器名>`，再 `docker compose up -d`
- 后端健康检查：`curl -s http://localhost:8080/healthcheck`
- 查看日志：`docker logs keep-backend --tail 20` / `docker logs keep-frontend --tail 20`

## 截图与临时文件
- 所有截图存放到 `.playwright-mcp/` 目录，**不要放项目根目录**
- 其他临时文件同理，不要污染项目根目录

## AI 模型配置
- 在设置页面「AI 配置」tab 中管理模型，支持多模型、多场景分配
- 配置存储在数据库中，通过 SecretManager 管理 API Key
- 不再使用环境变量配置模型（`OPENAI_API_KEY` 等已废弃）
- 后端服务：`keep/api/bl/ai_model_service.py`，API 路由：`keep/api/routes/ai_settings.py`

## 已完成的工作

### 1. OPENAI_BASE_URL 私有 LLM 支持
支持 GLM-5/Kimi-2.5/MiniMax-2.5 等 OpenAI 兼容接口：
- `keep/api/consts.py` — OPENAI_BASE_URL 常量
- `keep/api/bl/ai_suggestion_bl.py` — AI 告警聚类支持 base_url
- `keep/api/bl/incident_reports.py` — 事件报告支持 base_url
- `keep-ui/app/api/copilotkit/route.ts` — CopilotKit 前端支持 base_url
- `docker-compose.common.yml` — 环境变量透传

### 2. 中文文档翻译
- 翻译了 370 个文档文件到 `docs/zh-Hans/`
- 独立出 `docs-zh/` 目录，包含完整的中文文档结构
- 本地预览：`mintlify dev --port 3003`（目录 docs-zh）

### 3. AI 关联引擎自实现
- 替代商业版 External AI Transformers 的自托管方案
- 前端 → POST /ai/correlate → AISuggestionBl.suggest_incidents() → LLM API → 自动创建事件
- LLM 兼容：所有 OpenAI 兼容 API，通过 OPENAI_BASE_URL 环境变量配置
- 设计文档：`docs/ai-correlation-design.md`

### 4. AI 模型配置管理
- 数据库驱动的多模型/多场景配置（ai_model_config 表）
- 前端 AI 设置页面重构，支持动态模型和场景管理
- wiki：`wiki/260402-200535-AI模型配置管理设计.md`

## 历史问题参考

### LDAP 浏览器登录失败
- **原因：** `keep-frontend` 容器没加入 `keep-shared` Docker 网络，无法解析 `keep-backend`
- **修复：** `deploy/local-mac/docker-compose.yml` 给 frontend 加 `networks: [keep-shared]`



## ldap 登录

本地测试的ldap 登录账号的密码在这里可以查看，没有特别说明的话，你可以用里面的账号登录去测试和调试
/Users/fadewalk/Documents/mycode/keep/deploy/ldap/ldif