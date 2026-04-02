# Keep 项目记忆

## 分支策略
- `main` — 上游主分支（只同步，不推送）
- `develop` / `feature/*` — 本地开发分支（不推送上游）
- 不再使用 `feat/i18n-zh-CN` 分支，所有改动直接在 develop 或 feature 分支上做

## Remote 仓库
- **origin** — GitHub 个人仓库 (https://github.com/fadewalk/keep)
- **gitee** — Gitee 个人仓库 (https://gitee.com/wyule/keep)
- **upstream** — 官方仓库 (https://github.com/keephq/keep)

## 同步上游更新
```bash
git checkout main && git fetch upstream && git merge upstream/main
git push origin main
```

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
- 详情：[AI 关联引擎功能](memory/ai-correlation-feature.md)
- 设计文档：`docs/ai-correlation-design.md`

### 4. AI 模型配置管理
- 数据库驱动的多模型/多场景配置（ai_model_config 表）
- 前端 AI 设置页面重构，支持动态模型和场景管理
- 后端 API 路由 + 业务逻辑层完整实现
- wiki：`wiki/260402-200535-AI模型配置管理设计.md`

## 环境变量（私有 LLM）
```bash
OPENAI_API_KEY=your-private-llm-api-key
OPENAI_BASE_URL=http://your-private-llm-endpoint/v1
OPENAI_MODEL_NAME=glm-5  # 或 kimi-2.5、minimax-2.5 等
```

## 本地开发注意事项
- `.playwright-mcp/` 已加入 .gitignore
- 开发分支不推送上游
- 上游同步时手动 merge upstream/main
- Mintlify 本地 CLI 不支持 `languages` 配置，多语言切换是 Cloud-only

## 工作习惯
- [Git 提交和 Wiki 文档](memory/feedback_git_commit_and_wiki.md) — 完成设计/需求/修复后自动提交 git 并更新 wiki 文档

## 参考资料
- [LDAP 浏览器登录失败修复](memory/ldap-fix.md) — keep-shared network 和 LDAP 配置问题
- Obsidian 笔记目录：`/Users/fadewalk/Documents/mycode/obsidian/03-work/Keep/`
