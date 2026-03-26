# Docker 构建优化指南

## 背景

Keep 项目后端依赖较多（200+ Python 包），每次代码修改都要重新 `pip install` 安装全部依赖，构建时间过长。本方案通过**镜像分层**和**卷挂载**实现高效开发。

## 架构

```
┌─────────────────────────────────────────────────────────────┐
│                     构建阶段                                 │
├─────────────────────────────────────────────────────────────┤
│  Dockerfile.api-base                                        │
│  ├── python:3.13-slim-bookworm                             │
│  ├── 安装系统依赖 (gcc, libpq-dev, etc.)                    │
│  ├── 创建 venv                                             │
│  ├── pip install -r requirements.txt                        │
│  └── pip install -e . (安装 keep 包)                       │
│                                                             │
│  Dockerfile.api                                             │
│  └── 继承 api-base，只拷贝代码                              │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                     开发阶段                                 │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  docker-compose.dev.yml (推荐)                              │
│  ├── 使用 keep-api-base 镜像                               │
│  ├── 代码通过 volume 挂载 (/app/keep -> 源码目录)           │
│  └── 代码修改 → 秒级生效，无需 rebuild                       │
│                                                             │
│  docker-compose.yml (生产/完整构建)                         │
│  ├── 每次完整构建，但利用 Docker 缓存                         │
│  └── 依赖未变时，只重新拷贝代码层                            │
└─────────────────────────────────────────────────────────────┘
```

## 快速开始

### 1. 拉取基础镜像（首次执行）

由于 docker.io 在国内访问不稳定，建议从华为云镜像源拉取基础镜像：

```bash
# Python 基础镜像
docker pull swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/python:3.13-slim-bookworm-linuxarm64
docker tag swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/python:3.13-slim-bookworm-linuxarm64 docker.io/library/python:3.13-slim-bookworm

# Node 前端镜像
docker pull swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/node:20-alpine-linuxarm64
docker tag swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/node:20-alpine-linuxarm64 docker.io/library/node:20-alpine
```

### 2. 构建 Base 镜像（只需执行一次）

```bash
cd /Users/fadewalk/Documents/mycode/keep

# 构建 base 镜像（包含所有依赖，约 5-10 分钟）
# --cache-from 复用本地已有镜像的层，加速构建
docker build -f docker/Dockerfile.api-base \
  --cache-from=keep-api-base:latest \
  -t keep-api-base:latest .
```

### 3. 日常开发

```bash
# 方式一：开发模式（推荐，代码修改秒级生效）
docker compose -f deploy/local-mac/docker-compose.dev.yml up -d

# 方式二：完整构建（依赖变更后使用）
docker compose -f deploy/local-mac/docker-compose.yml up --build -d
```

### 4. 代码修改后

**方式一（dev 模式）：**
- 直接修改代码，刷新浏览器即可看到效果
- 如需重启后端：`docker compose -f deploy/local-mac/docker-compose.dev.yml restart keep-backend`

**方式二（完整构建）：**
- `docker compose -f deploy/local-mac/docker-compose.yml up --build -d`
- 利用 Docker 缓存，依赖层不会重新安装

## 文件说明

| 文件 | 说明 |
|------|------|
| `docker/Dockerfile.api-base` | Base 镜像构建文件，包含系统依赖和 Python 包 |
| `docker/Dockerfile.api-dev` | 开发用 Dockerfile（继承 base） |
| `docker/Dockerfile.api` | 生产用 Dockerfile（完整构建） |
| `deploy/local-mac/docker-compose.dev.yml` | 开发用 compose（使用 volume 挂载） |
| `deploy/local-mac/docker-compose.yml` | 完整构建用 compose |

## 工作流对比

| 场景 | dev 模式 | 完整构建模式 |
|------|----------|--------------|
| 首次构建 | 5-10 分钟（构建 base）+ 10 秒（启动） | 10-15 分钟 |
| 修改 Python 代码 | **秒级生效** | 1-2 分钟（拷贝 + 重启） |
| 修改依赖 | 需 rebuild base 镜像 | 需 rebuild |
| 适合场景 | 日常开发、调试 | 依赖变更后验证 |

## 注意事项

1. **依赖变更**：修改 `requirements.txt` 或 `pyproject.toml` 后，需要重新构建 base：
   ```bash
   docker build -f docker/Dockerfile.api-base \
     --cache-from=keep-api-base:latest \
     -t keep-api-base:latest .
   ```

2. **清理缓存**（如遇构建异常）：
   ```bash
   docker system prune -a
   ```

3. **Windows/Mac 文件系统**：volume 挂载在某些 IDE 环境下可能存在文件监听问题，重启容器即可：
   ```bash
   docker compose -f deploy/local-mac/docker-compose.dev.yml restart keep-backend
   ```

4. **缓存复用原理**：`--cache-from` 会从指定镜像的层缓存中复用，即使某些层需要重新构建，也能最大程度利用已有缓存。如果想强制重新构建某个阶段，可以使用 `--no-cache` 配合 `--cache-from` 仅针对特定阶段清除缓存。
