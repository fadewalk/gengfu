# 本地 Mac 部署

用于在本地 Mac 上通过 Docker Compose 部署完整的 Keep 平台（前端 + 后端 + WebSocket）。

## 前置要求

- Docker Desktop for Mac（已安装并运行）
- 确保项目根目录下有 `state/` 文件夹（首次启动会自动创建）

## 服务组成

| 服务 | 说明 | 端口 | Dockerfile |
|------|------|------|------------|
| keep-backend | Python API 后端 (Gunicorn + Uvicorn) | 8080 | `docker/Dockerfile.api` |
| keep-frontend | Next.js 前端 (Node.js 20 Alpine) | 3000 | `deploy/local-mac/Dockerfile.ui` |
| keep-websocket-server | Soketi WebSocket 服务 | 6001, 9601 | `quay.io/soketi/soketi:1.4-16-debian` |

## 启动

### 一键 build + 启动

```bash
cd /Users/fadewalk/Documents/mycode/keep/deploy/local-mac
docker compose up --build -d
```

### 分步 build + 启动（推荐）

先 build 再启动，镜像就绪后访问不用等待：

```bash
cd /Users/fadewalk/Documents/mycode/keep/deploy/local-mac
docker compose build
docker compose up -d
```

### 常用命令

```bash
# 查看运行状态
docker compose ps

# 查看日志
docker compose logs -f              # 所有服务
docker compose logs -f keep-backend  # 只看后端
docker compose logs -f keep-frontend # 只看前端

# 停止（保留数据）
docker compose down

# 停止并清除数据卷（慎用）
docker compose down -v
```

### 单独重编译

```bash
# 只编译后端
docker compose build keep-backend && docker compose up -d keep-backend

# 只编译前端
docker compose build keep-frontend && docker compose up -d keep-frontend
```

## 访问地址

- 前端：http://localhost:3000
- 后端 API：http://localhost:8080
- WebSocket：ws://localhost:6001

默认 `AUTH_TYPE=NO_AUTH`，无需登录。

## 环境变量配置

### 基础配置（docker-compose.yml）

| 变量 | 默认值 | 说明 |
|------|--------|------|
| AUTH_TYPE | NO_AUTH | 认证方式，本地开发建议 NO_AUTH |
| API_URL | http://keep-backend:8080 | 前端访问后端的内部地址 |
| SENTRY_DISABLED | true | 禁用 Sentry 错误上报 |

### AI 功能（继承自 docker-compose.common.yml）

支持私有 LLM（GLM-5/Kimi/MiniMax 等 OpenAI 兼容接口），在宿主机设置环境变量即可透传：

```bash
export OPENAI_API_KEY=your-api-key
export OPENAI_BASE_URL=http://your-llm-endpoint/v1
export OPENAI_MODEL_NAME=glm-5
```

然后在 `deploy/local-mac` 目录下执行 `docker compose up -d`。

### 数据库

默认使用 SQLite，数据文件位于 `state/db.sqlite3`。

### Pusher/WebSocket 配置

| 变量 | 值 | 说明 |
|------|------|------|
| PUSHER_APP_KEY | keepappkey | Pusher 应用 Key |
| PUSHER_PORT | 6001 | WebSocket 端口 |

## 数据持久化

所有数据存储在项目根目录 `state/` 文件夹：

```
state/
├── db.sqlite3          # SQLite 数据库
└── ...                 # Secret Manager 文件等
```

## 架构说明

```
docker-compose.yml          ← 本地部署定义（AUTH_TYPE=NO_AUTH）
    │
    ├── extends ──→ docker-compose.common.yml  ← 公共配置（端口、环境变量）
    │
    ├── keep-backend  ──→ docker/Dockerfile.api   ← Python 后端镜像
    ├── keep-frontend ──→ deploy/local-mac/Dockerfile.ui ← 前端镜像
    └── keep-websocket-server ──→ soketi 官方镜像
```

## 常见问题

### build 失败：网络问题

前端 `npm ci` 可能因网络超时失败，可配置 Docker 代理：

```bash
# 在 ~/.docker/config.json 中配置代理
# 或在 docker-compose.yml 中添加 build args
```

### 端口被占用

```bash
# 查看占用
lsof -i :3000
lsof -i :8080

# 修改端口：编辑 docker-compose.common.yml 中的 ports 映射
```

### 本地开发替代方案

如果需要频繁修改代码，建议前后端分别本地运行（支持热更新）：

```bash
# 后端
cd keep
pip install -e .
python -m keep.api

# 前端
cd keep-ui
npm install
npm run dev
```
