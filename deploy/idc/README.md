# Keep IDC 离线部署指南

## 概述

本目录包含 Keep 在 **无法访问外网的 IDC 机房** 中部署所需的所有配置文件。

已移除/禁用的外网依赖：

| 组件 | 状态 | 说明 |
|------|------|------|
| PostHog 遥测 | 已禁用 | 环境变量 `POSTHOG_DISABLED=true` |
| Sentry 错误追踪 | 已禁用 | 不设置 `NEXT_PUBLIC_SENTRY_DSN` |
| Monaco Editor CDN | 已本地化 | 从 `node_modules` 复制到 `public/` |
| Next.js 遥测 | 已禁用 | `NEXT_TELEMETRY_DISABLED=1` |
| Google Fonts | 无需处理 | `next/font/google` 在构建时内联，运行时不需要外网 |
| 外部登录图片 | 可忽略 | 仅移动端登录页，桌面端不触发 |
| AI/LLM | 可选 | 不配置 API Key 则自动隐藏 |

## 文件说明

```
deploy/idc/
├── README.md           # 本文档
├── .env                # 环境变量模板
├── docker-compose.yml  # 编排文件
├── Dockerfile.ui       # 前端构建（无 CDN 依赖）
└── Dockerfile.api      # 后端构建（禁用遥测）
```

## 前置条件

### 1. 构建环境要求

构建镜像需要一台 **能访问外网的机器**（开发机或 CI runner），构建完成后将镜像导出传到 IDC。

### 2. 镜像准备

在有网络的机器上构建：

```bash
# 克隆代码
git clone <repo_url> keep && cd keep

# 构建镜像
docker compose -f deploy/idc/docker-compose.yml build

# 导出镜像为 tar 文件
docker save keep-idc-keep-frontend:latest -o keep-frontend.tar
docker save keep-idc-keep-backend:latest -o keep-backend.tar
docker pull quay.io/soketi/soketi:1.4-16-debian
docker save quay.io/soketi/soketi:1.4-16-debian -o soketi.tar
```

### 3. 传输到 IDC

```bash
scp keep-frontend.tar keep-backend.tar soketi.tar user@idc-server:/opt/keep/
```

### 4. IDC 上加载镜像

```bash
ssh user@idc-server
cd /opt/keep
docker load -i keep-frontend.tar
docker load -i keep-backend.tar
docker load -i soketi.tar
```

## 部署步骤

### 1. 配置环境变量

```bash
cp .env .env.local
# 编辑 .env.local，修改以下关键变量：
vi .env.local
```

必须修改的变量：

```bash
# 域名/IP
NEXTAUTH_URL=http://YOUR_IDC_IP:4000
NEXT_PUBLIC_API_URL=http://YOUR_IDC_IP:8080
KEEP_API_URL=http://YOUR_IDC_IP:8080

# 安全密钥（生产环境必须修改）
NEXTAUTH_SECRET=$(openssl rand -hex 32)
```

### 2. 启动服务

```bash
docker compose -f deploy/idc/docker-compose.yml --env-file .env.local up -d
```

### 3. 验证

```bash
# 检查服务状态
docker compose -f deploy/idc/docker-compose.yml ps

# 前端
curl http://YOUR_IDC_IP:4000

# 后端健康检查
curl http://YOUR_IDC_IP:8080/healthcheck
```

## 可选：使用 MySQL

编辑 `docker-compose.yml`，取消 mysql 服务的注释，然后修改 `.env`：

```bash
DATABASE_CONNECTION_STRING=mysql+pymysql://keep:keep_idc_password@mysql:3306/keep
```

## 可选：使用内网 AI

如果 IDC 内部部署了 LLM 服务（如 vLLM、Ollama）：

```bash
OPENAI_API_KEY=your-internal-key
OPENAI_BASE_URL=http://internal-llm:8000/v1
OPENAI_MODEL_NAME=your-model
```

## 可选：使用 LDAP/Keycloak 认证

```bash
# LDAP
AUTH_TYPE=LDAP
LDAP_URL=ldap://internal-ldap:389
LDAP_BIND_DN=cn=admin,dc=company,dc=com
LDAP_BIND_PASSWORD=password
LDAP_BASE_DN=ou=users,dc=company,dc=com

# Keycloak
AUTH_TYPE=KEYCLOAK
KEYCLOAK_URL=http://internal-keycloak:8080
```

## 端口说明

| 端口 | 服务 | 说明 |
|------|------|------|
| 4000 | 前端 | Next.js Web UI |
| 8080 | 后端 | FastAPI |
| 6001 | WebSocket | Soketi (实时推送) |

## 故障排查

### 前端页面加载慢或白屏

检查 Monaco Editor 是否正常加载：
```bash
curl http://YOUR_IDC_IP:4000/monaco-vs/vs/loader.js
```
如果 404，说明构建时 Monaco 静态资源未正确复制。

### 后端启动失败

```bash
docker compose logs keep-backend
```

常见问题：
- 数据库连接失败 → 检查 `DATABASE_CONNECTION_STRING`
- 权限问题 → 检查 `/state` 目录权限
