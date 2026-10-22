# 更夫快速上手：从安装到收到第一条钉钉告警

> 目标：10 分钟内完成 部署 → 接入监控源 → 配置钉钉 → 收到告警通知 的完整闭环。
> 前置要求：一台能跑 Docker 的主机（Linux / macOS 均可），钉钉群一个。

## 第 1 步：部署（2 分钟）

```bash
mkdir gengfu && cd gengfu
curl -O https://raw.githubusercontent.com/fadewalk/gengfu/main/docker-compose.yml
docker compose up -d
```

等容器全部 healthy 后打开 `http://localhost:4000`。默认 NO_AUTH 免认证模式（内网试用），
生产环境请参考 [docker-compose.yml](https://github.com/fadewalk/gengfu/blob/main/docker-compose.yml) 内的注释配置 LDAP 认证与 MySQL。

## 第 2 步：接入监控源（3 分钟）

更夫不替代监控，而是承接监控的告警。以最常用的两种方式为例：

**方式 A：Prometheus（remote_write / Alertmanager webhook）**

在 Prometheus 的 `alertmanager.yml` 中把告警发到更夫：

```yaml
receivers:
  - name: gengfu
    webhook_configs:
      - url: http://<更夫地址>:8080/alerts/event/prometheus
```

**方式 B：任意系统（通用 Webhook）**

任何能发 HTTP POST 的系统都可以接入，更夫会自动解析常见告警格式。
在更夫界面「Providers → Webhook」里安装一个 webhook provider 即可获得专属地址。

接入成功后，更夫「Alerts」页会出现你的告警。

## 第 3 步：配置钉钉机器人（3 分钟）

1. 钉钉群里「设置 → 机器人 → 添加机器人 → 自定义」，安全设置选**加签**，复制 `SEC` 密钥
2. 复制 Webhook URL 中 `access_token=` 之后的参数
3. 更夫界面「Providers」→ 搜索 **DingTalk** → 填入 `access_token` 与 `secret` → 连接
   - 实例名建议就叫 `dingtalk`（与内置模板的引用名一致）

企业微信 / 飞书的接入方法见 [providers 文档目录](https://github.com/fadewalk/gengfu/tree/main/keep/providers)，
其中飞书编程套餐订阅 key 的用法见[兼容性文档](https://github.com/fadewalk/gengfu/blob/main/docs/llm-compatibility-zh.md)。

## 第 4 步：启用内置工作流模板（1 分钟）

打开「Workflows → Templates」，搜索「更夫」，选择「**更夫 · Prometheus 告警钉钉通知**」启用。

内置的国内场景模板：

| 模板 | 链路 |
|---|---|
| 更夫 · Prometheus 告警钉钉通知 | Prometheus critical 告警 → 钉钉卡片 + 查看详情 |
| 更夫 · Zabbix 告警企业微信通知 | Zabbix 告警 → 企微（可 @ 值班人） |
| 更夫 · 告警飞书卡片通知 | 高危告警 → 飞书卡片（按严重度配色） |

## 第 5 步：触发一条测试告警（1 分钟）

用 curl 模拟一条 critical 告警：

```bash
curl -X POST http://localhost:8080/alerts/event/prometheus \
  -H "Content-Type: application/json" \
  -d '{
    "alerts": [{
      "labels": {
        "alertname": "HighCPUUsage",
        "severity": "critical",
        "instance": "web-01:9100"
      },
      "annotations": {
        "summary": "CPU 使用率 95%",
        "description": "web-01 CPU 使用率超过 90%，持续 5 分钟"
      },
      "status": "firing"
    }]
  }'
```

几秒内钉钉群应收到卡片消息。没收到？按顺序检查：
1. 更夫「Workflows」页该工作流是否有执行记录（有记录但没收到 → 检查钉钉 token/加签密钥）
2. 告警的 `severity` 是否为 `critical`（模板只转发 critical）
3. 后端日志：`docker logs gengfu-backend`

## 进阶

- **AI 事件报告**：告警聚合为事件后，事件页点「报告」可生成中文分析报告（Settings → AI Configuration 里配 DeepSeek / GLM 等，兼容性实测见 [llm-compatibility-zh.md](https://github.com/fadewalk/gengfu/blob/main/docs/llm-compatibility-zh.md)）
- **告警降噪**：多个同源告警会自动去重聚合；自定义去重规则见设置页
- **海外集成**：默认隐藏了 54 个海外 SaaS，设置页「提供商可见性」可随时打开
- **值班排班与更多工作流语法**：见上游文档（英文）
