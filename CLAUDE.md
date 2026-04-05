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
- `develop` — 本地开发分支
- 功能分支从 `develop` 创建，合并后可删除

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
- 不需要用户提醒提交，完成后自动执行 git add/commit

## 截图与临时文件
- 所有截图（Playwright、浏览器截图等）存放到 `.playwright-mcp/` 目录，**不要放项目根目录**
- 其他临时文件同理，不要污染项目根目录

## AI 模型配置
- 在设置页面「AI 配置」tab 中管理模型，支持多模型、多场景分配
- 配置存储在数据库中，通过 SecretManager 管理 API Key
- 不再使用环境变量配置模型（`OPENAI_API_KEY` 等已废弃）
- 后端服务：`keep/api/bl/ai_model_service.py`，API 路由：`keep/api/routes/ai_settings.py`
