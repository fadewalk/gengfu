# Prometheus + Alertmanager 本地开发环境

## 架构概览

```
node_exporter (Mac本地:9100)
        │
        ▼
  Prometheus Docker (9090)
        │
        ▼ (告警规则触发)
  Alertmanager Docker (9093)
        │
        ▼ (webhook)
  Keep Backend (8080)
        /alerts/event/prometheus
```

## 组件说明

| 组件 | Docker 容器名 | 端口 | 用途 |
|------|--------------|------|------|
| Prometheus | `local-prometheus` | 9090 | 指标采集 + 告警规则引擎 |
| Alertmanager | `local-alertmanager` | 9093 | 告警收敛 + 转发到 Keep |
| node_exporter | Mac 本地运行 | 9100 | 机器指标采集 (CPU/内存/磁盘) |

## 配置文件

配置文件统一放在项目根目录 `state/` 下：

```
state/
├── prometheus.yml      # Prometheus 采集配置
├── alert.rules         # Prometheus 告警规则
├── alertmanager.yml    # Alertmanager 路由配置
└── prometheus_data/    # Prometheus TSDB 数据持久化
```

## docker-compose.yml 中的配置

`deploy/local-mac/docker-compose.yml` 新增了以下 service：

```yaml
prometheus:
  image: prom/prometheus:v2.54.0
  container_name: local-prometheus
  command:
    - '--config.file=/etc/prometheus/prometheus.yml'
    - '--storage.tsdb.path=/prometheus'
    - '--web.enable-lifecycle'      # 支持热加载
  ports:
    - "9090:9090"
  volumes:
    - ../../state/prometheus.yml:/etc/prometheus/prometheus.yml:ro
    - ../../state/alert.rules:/etc/prometheus/alert.rules:ro
    - ../../state/prometheus_data:/prometheus
  extra_hosts:
    - "host.docker.internal:host-gateway"
  restart: unless-stopped

alertmanager:
  image: prom/alertmanager:v0.27.0
  container_name: local-alertmanager
  ports:
    - "9093:9093"
  volumes:
    - ../../state/alertmanager.yml:/etc/alertmanager/alertmanager.yml:ro
  extra_hosts:
    - "host.docker.internal:host-gateway"
  restart: unless-stopped
```

## 各配置文件内容

### state/prometheus.yml
- scrape `host.docker.internal:9100` → 采集 node_exporter 指标 (Mac 本机)
- scrape `host.docker.internal:8080` → 采集 Keep 后端指标
- alerting 配置指向 `local-alertmanager:9093`
- 告警规则文件 `/etc/prometheus/alert.rules`

### state/alert.rules
包含 4 个测试告警规则 (阈值设得很低，易触发)：
- `HighCPU` - CPU > 1% 触发
- `HighMemory` - 内存 > 1% 触发
- `HighDiskUsage` - 磁盘 > 1% 触发
- `TestAlertAlwaysFiring` - `up == 1` 始终触发

### state/alertmanager.yml
- 全局 `resolve_timeout: 1m`
- 路由到 `keep-webhook` receiver
- webhook 地址 `http://host.docker.internal:8080/alerts/event/prometheus`
- 认证方式：Bearer Token，Token 为 Keep 的 API Key

## node_exporter 安装 (Mac)

如果你本地没有 node_exporter，需要安装：

```bash
# 使用 Homebrew 安装
brew install node_exporter

# 启动 (默认端口 9100)
brew services start node_exporter

# 验证
curl http://localhost:9100/metrics | head
```

> ⚠️ 如果 Mac 上有多个 node_exporter 进程，确保只运行一个且端口不冲突

## 常用命令

```bash
# 进入部署目录
cd deploy/local-mac

# 启动所有容器
docker compose up -d

# 查看容器状态
docker compose ps

# 查看 Prometheus 日志
docker logs local-prometheus -f

# 查看 Alertmanager 日志
docker logs local-alertmanager -f

# 热加载 Prometheus 配置 (无需重启容器)
docker exec local-prometheus kill -HUP 1

# 手动触发 Prometheus 规则重新评估
curl -X POST http://localhost:9090/-/reload

# 验证 Prometheus → Alertmanager 连通性
docker exec local-prometheus wget -O- -q http://local-alertmanager:9093/-/healthy
```

## 验证告警是否触发

```bash
# 查看 Prometheus 中的告警状态
curl -s http://localhost:9090/api/v1/alerts | jq '.data.alerts[] | {name: .labels.alertname, state: .state}'

# 查看 Prometheus 规则是否加载
curl -s http://localhost:9090/api/v1/rules | jq '.data.groups[].rules[] | {name: .name, type: .type}'

# 查看 Alertmanager 收到的告警
curl -s http://localhost:9093/api/v2/alerts | jq .

# 直接向 Keep 发送测试告警 (绕过 Prometheus→Alertmanager)
curl -X POST http://localhost:8080/alerts/event/prometheus \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer bc285d39-45be-46ca-8cde-7696e2d71ac5" \
  -d '[
    {
      "labels": {
        "alertname": "TestAlert",
        "severity": "warning",
        "instance": "test"
      },
      "annotations": {
        "summary": "测试告警",
        "description": "这是一条测试告警"
      },
      "startsAt": "2026-03-25T00:00:00Z"
    }
  ]'
```

## 关键调试发现

1. **Docker 网络**：`host.docker.internal` 在 Docker 外部指向宿主机，在 Docker 内部需要 `extra_hosts` 映射
2. **Alertmanager endpoint**：Keep 的 Prometheus webhook 端点是 `/alerts/event/prometheus`，不是 `/prometheus/v1/webhook`
3. **Bearer Token**：Keep NO_AUTH 模式下使用 API Key 作为 Bearer Token 认证
4. **Prometheus 热加载**：修改 `alert.rules` 后需要 `kill -HUP` 或 POST `/-/reload` 触发重载
5. **规则路径**：Docker 内 `rule_files` 路径是容器内路径，不是宿主机路径
