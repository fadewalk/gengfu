# 接入夜莺（Nightingale）

更夫不替代夜莺的监控与告警判定，而是承接夜莺产生告警之后的降噪、值班、事件与 AI 分析。推荐接入方式是夜莺的 **Webhook 通知**。

## 第一步：获取更夫的 Webhook 地址

1. 更夫界面「Providers」→ 搜索 **Webhook** → 安装，实例名建议设为 `webhook`
2. 安装后复制生成的 Webhook URL（形如 `http://<更夫地址>:8080/alerts/event/webhook?provider_name=webhook`）

## 第二步：夜莺配置通知

夜莺 6.x / 7.x 均支持 HTTP 通知：

1. 「告警管理 → 通知规则 → 新增」，或「告警 → 通知媒介」按版本不同入口略有差异
2. 通知方式选择 **HTTP**，地址填入上一步的更夫 Webhook URL
3. 请求方法 `POST`，内容保持默认 JSON（夜莺会推送完整事件结构，更夫自动解析）
4. 保存并把该通知规则绑定到你的告警规则

推一条测试告警后，更夫「Alerts」页应出现 source 为 `webhook` 的告警。

## 第三步：启用更夫内置工作流模板

「Workflows → Templates」搜索「夜莺」，启用「**更夫 · 夜莺告警钉钉通知**」。

模板默认转发 `critical` / `warning` 级别，如需自定义过滤条件（例如只转发特定业务组），修改模板触发器中的 CEL 表达式：

```yaml
triggers:
  - type: alert
    cel: source.contains("webhook") && severity in ["critical", "warning"]
    # 只转发指定业务组示例：
    # cel: source.contains("webhook") && labels.busigroup.contains("支付")
```

## 常见问题

- **告警没进来**：先确认夜莺的 HTTP 通知日志有成功响应（更夫返回 `task_name` 即受理）；再查更夫「Alerts」页有无 source=webhook 的记录
- **想区分多个夜莺**：安装多个 Webhook provider 实例（如 `webhook-n9e-prod`、`webhook-n9e-pre`），更夫按 provider 实例区分来源
- **告警风暴**：夜莺侧已收敛仍量大时，在更夫设置页配置去重规则做二次聚合

## 相关

- 夜莺官方文档：https://n9e.github.io/
- 更夫去重与告警聚合：界面内「Deduplication」设置
