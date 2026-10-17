<div align="center">
    <img src="/assets/keep.png?raw=true" width="86">
</div>

<h1 align="center">更夫 Gengfu</h1>

<h4 align="center">开源的告警聚合与 AI 事件管理平台 · 面向中国企业场景的 Keep 中文发行版</h4>

</br>

<div align="center">监控交给夜莺们，告警之后的事交给更夫——降噪去重、值班通知、事件管理、AI 分析、自动化处置。
</br>
</div>

<div style="width: 100%; max-width: 800px; margin: 0 auto;">
    <img
        src="/assets/sneaknew.png?raw=true"
        style="width: 100%; height: auto; object-fit: contain;"
        alt="Sneak preview screenshot"
    >
</div>

<h1 align="center"></h1>

- 🔍 **统一视图** - 用于所有告警和事件的最佳可定制界面
- 🛠️ **告警多功能助手** - 去重、关联、过滤与丰富
- 🔄 **深度集成** - 与监控工具双向同步，并支持自定义工作流
- ⚡ **[自动化](#工作流)** - 为你的监控工具提供 GitHub Actions
- 🤖 **AI 事件分析** - AI 驱动的关联与摘要、中文事件报告，支持 DeepSeek / Qwen / GLM 等国产大模型

</br>

## 为什么做这个项目

上游 [Keep](https://github.com/keephq/keep) 是一款优秀的开源 AIOps 平台：477 个监控/工单/通信集成、声明式工作流引擎、AI 告警关联，这些能力在国内没有同量级的开源替代。但它是围绕海外生态设计的，直接放进国内企业环境，"能跑起来，却用不起来"：

- **集成断供**：477 个集成里没有钉钉、企业微信、飞书，也没有阿里云/腾讯云监控——国内团队最高频的告警触达渠道一个都没有，只能靠通用 webhook 兜底；
- **默认值不匹配**：界面与 AI 提示词默认英文，AI 后端默认 OpenAI/Anthropic，国产大模型要自己想办法接；
- **部署假设不同**：认证默认对接 Auth0/Okta 等 SaaS IdP，与国内企业内网环境（LDAP、受限外网）有距离。

而国内的另一头，监控采集层已经非常成熟——Zabbix、Prometheus、夜莺、云厂商监控各司其职。真正碎片化、没人管的是**告警之后的第一公里**：告警风暴无人收敛、值班靠人肉盯群、事件处置没有沉淀、AI 分析基本空白。商业 AIOps（智能告警收敛方向）客单价在百万级，中小企业用不起；开源侧只有 PrometheusAlert 这类"消息转发器"，没有完整的聚合、事件与 AI 平台。

这个空档就是本项目的立足点：**以 MIT 协议的 Keep 为底座，做一款中国企业场景真正可用的开源告警聚合与 AI 事件管理平台。** 中文化只是第一层，核心是补上国内生态的三块短板：国内 IM 触达、国产大模型接入、内网私有化部署。

## 为什么叫「更夫」

更夫是古代的夜间值守人：巡夜、报时，发现火情就敲锣示警，把要紧的警讯送到该听到的人耳朵里。他做的事正是这个产品做的事——**值守（on-call）、分辨真警讯、把对的通知发给对的人**。产品的告警通知里也保留了这个彩蛋：「天干物燥，小心火烛」。

## 定位与边界

监控采集不归更夫管——Zabbix、Prometheus、夜莺、云监控继续各司其职。更夫承接的是告警产生之后的一切：

```
监控层（夜莺 / Prometheus / Zabbix / 云监控 / 日志系统）
        │  webhook / API 接入
        ▼
更夫：接入汇聚 → 去重降噪关联 → 值班与通知（钉钉 / 企微 / 飞书）
        → 事件管理 → AI 分析与报告 → 工作流自动化处置
```

## 已完成与路线图

**已完成**

- 全模块界面中文化（zh-CN）
- AI 提示词与事件报告中文输出：多模板报告、报告聊天历史持久化
- 内网私有化部署套件（`deploy/idc/`）：LDAP 认证、无 Redis 降级运行、VictoriaMetrics 监控栈
- AI 模型数据库化配置：OpenAI 兼容接口直连 DeepSeek / Qwen / GLM 等国产模型
- 国内 IM 三件套原生 provider：钉钉（加签/关键词）、企业微信（@手机号）、飞书（签名/卡片）

**进行中 / 计划**

- 定期合并上游更新（上游修复节奏约每季度近百个提交）
- 海外 SaaS 集成（PagerDuty、ServiceNow、Slack 等）转为默认关闭的可选项
- 国产大模型兼容矩阵：验证工具已就绪（`scripts/verify_llm_compat.py`），待接入各家 API key 实测并产出矩阵
- 企业微信/飞书 @ 指定值班人（需开放平台 user_id 映射）

## 与上游 Keep 的关系

本仓库是 [keephq/keep](https://github.com/keephq/keep)（MIT License）的中文发行版，品牌独立、代码血缘透明：我们定期合并上游更新，有普适价值的改动也会回馈上游。MIT 许可证与版权声明完整保留，致谢见文末。

</br>

## 支持的集成

### 用于丰富、关联与事件上下文的 AI 后端

<table>
<tr>
    <td align="center" width="150">
        <a>
            <img width="40" src="keep-ui/public/icons/anthropic-icon.png" alt="Anthropic"/><br/>
            Anthropic
        </a>
    </td>
    <td align="center" width="150">
        <a>
            <img width="40" src="keep-ui/public/icons/openai-icon.png" alt="OpenAI"/><br/>
            OpenAI
        </a>
    </td>
    <td align="center" width="150">
        <a>
            <img width="40" src="keep-ui/public/icons/deepseek-icon.png" alt="DeepSeek"/><br/>
            DeepSeek
        </a>
    </td>
    <td align="center" width="150">
        <a>
            <img width="40" src="keep-ui/public/icons/ollama-icon.png" alt="Ollama"/><br/>
            Ollama
        </a>
    </td>
    <td align="center" width="150">
        <a>
            <img width="40" src="keep-ui/public/icons/llamacpp-icon.png" alt="LlamaCPP"/><br/>
            LlamaCPP
        </a>
    </td>
    <td align="center" width="150">
        <a>
            <img width="40" src="keep-ui/public/icons/grok-icon.png" alt="Grok"/><br/>
            Grok
        </a>
    </td>
</tr>
<tr>
    <td align="center" width="150">
        <a>
            <img width="40" src="keep-ui/public/icons/gemini-icon.png" alt="Gemini"/><br/>
            Gemini
        </a>
    </td>
</tr>
</table>

### 可观测性工具

<table>
<tr>
    <td align="center" width="150">
        <a>
            <img width="40" src="keep-ui/public/icons/appdynamics-icon.png" alt="AppDynamics"/><br/>
            AppDynamics
        </a>
    </td>
    <td align="center" width="150">
        <a>
            <img width="40" src="keep-ui/public/icons/axiom-icon.png" alt="Axiom"/><br/>
            Axiom
        </a>
    </td>
    <td align="center" width="150">
        <a>
            <img width="40" src="keep-ui/public/icons/azuremonitoring-icon.png" alt="Azure Monitoring"/><br/>
            Azure Monitoring
        </a>
    </td>
    <td align="center" width="150">
        <a>
            <img width="40" src="keep-ui/public/icons/centreon-icon.png" alt="Centreon"/><br/>
            Centreon
        </a>
    </td>
    <td align="center" width="150">
        <a>
            <img width="40" src="keep-ui/public/icons/checkmk-icon.png" alt="Checkmk"/><br/>
            Checkmk
        </a>
    </td>
    <td align="center" width="150">
        <a>
            <img width="40" src="keep-ui/public/icons/cilium-icon.png" alt="Cilium"/><br/>
            Cilium
        </a>
    </td>
</tr>
<tr>
    <td align="center" width="150">
        <a>
            <img width="40" src="keep-ui/public/icons/checkly-icon.png" alt="Checkly"/><br/>
            Checkly
        </a>
    </td>
    <td align="center" width="150">
        <a>
            <img width="40" src="keep-ui/public/icons/cloudwatch-icon.png" alt="CloudWatch"/><br/>
            CloudWatch
        </a>
    </td>
    <td align="center" width="150">
        <a>
            <img width="40" src="keep-ui/public/icons/coralogix-icon.png" alt="Coralogix"/><br/>
            Coralogix
        </a>
    </td>
    <td align="center" width="150">
        <a>
            <img width="40" src="keep-ui/public/icons/dash0-icon.png" alt="Dash0"/><br/>
            Dash0
        </a>
    </td>
    <td align="center" width="150">
        <a>
            <img width="40" src="keep-ui/public/icons/datadog-icon.png" alt="Datadog"/><br/>
            Datadog
        </a>
    </td>
    <td align="center" width="150">
        <a>
            <img width="40" src="keep-ui/public/icons/dynatrace-icon.png" alt="Dynatrace"/><br/>
            Dynatrace
        </a>
    </td>
  </tr>
  <tr>
    <td align="center">
        <a>
            <img width="40" src="keep-ui/public/icons/elastic-icon.png" alt="Elastic"/><br/>
            Elastic
        </a>
    </td>
    <td align="center">
        <a>
            <img width="40" src="keep-ui/public/icons/gcpmonitoring-icon.png" alt="GCP Monitoring"/><br/>
            GCP Monitoring
        </a>
    </td>
    <td align="center" width="150">
        <a>
            <img width="40" src="keep-ui/public/icons/grafana-icon.png" alt="Grafana"/><br/>
            Grafana
        </a>
    </td>
    <td align="center" width="150">
        <a>
            <img width="40" src="keep-ui/public/icons/grafana_loki-icon.png" alt="Grafana Loki"/><br/>
            Grafana Loki
        </a>
    </td>
    <td align="center" width="150">
        <a>
            <img width="40" src="keep-ui/public/icons/graylog-icon.png" alt="Graylog"/><br/>
            Graylog
        </a>
    </td>
    <td align="center" width="150">
    <a>
        <img width="40" src="keep-ui/public/icons/icinga2-icon.png" alt="Icinga2"/>
        <br/>
        Icinga2
    </a>
    </td>
  </tr>
  <tr>
    <td align="center" width="150">
        <a>
            <img width="40" src="keep-ui/public/icons/kibana-icon.png" alt="Kibana"/><br/>
            Kibana
        </a>
    </td>
    <td align="center" width="150">
        <a>
            <img width="40" src="keep-ui/public/icons/libre_nms-icon.png" alt="LibreNMS"/><br/>
            LibreNMS
        </a>
    </td>
    <td align="center" width="150">
        <a>
            <img width="40" src="keep-ui/public/icons/netbox-icon.png" alt="NetBox"/><br/>
            NetBox
        </a>
    </td>
    <td align="center" width="150">
        <a>
            <img width="40" src="keep-ui/public/icons/netdata-icon.png" alt="Netdata"/><br/>
            Netdata
        </a>
    </td>
    <td align="center" width="150">
        <a>
            <img width="40" src="keep-ui/public/icons/newrelic-icon.png" alt="New Relic"/><br/>
            New Relic
        </a>
    </td>
    <td align="center" width="150">
        <a>
            <img width="40" src="keep-ui/public/icons/opensearchserverless-icon.png" alt="OpenSearch Serverless"/><br/>
            OpenSearch Serverless
        </a>
    </td>

</tr>
<tr>
    <td align="center" width="150">
        <a>
            <img width="40" src="keep-ui/public/icons/parseable-icon.png" alt="Parseable"/><br/>
            Parseable
        </a>
    </td>
    <td align="center" width="150">
        <a>
            <img width="40" src="keep-ui/public/icons/pingdom-icon.png" alt="Pingdom"/><br/>
            Pingdom
        </a>
    </td>
    <td align="center" width="150">
        <a>
            <img width="40" src="keep-ui/public/icons/prometheus-icon.png" alt="Prometheus"/><br/>
            Prometheus
        </a>
    </td>
    <td align="center" width="150">
        <a>
            <img width="40" src="keep-ui/public/icons/rollbar-icon.png" alt="Rollbar"/><br/>
            Rollbar
        </a>
    </td>
    <td align="center" width="150">
        <a>
            <img width="40" src="keep-ui/public/icons/sentry-icon.png" alt="Sentry"/><br/>
            Sentry
        </a>
    </td>
    <td align="center" width="150">
        <a>
            <img width="40" src="keep-ui/public/icons/signalfx-icon.png" alt="SignalFX"/><br/>
            SignalFX
        </a>
    </td>

</tr>
<tr>
    <td align="center" width="150">
        <a>
            <img width="40" src="keep-ui/public/icons/openobserve-icon.png" alt="OpenObserve"/><br/>
            OpenObserve
        </a>
    </td>
    <td align="center" width="150">
        <a>
            <img width="40" src="keep-ui/public/icons/site24x7-icon.png" alt="Site24x7"/><br/>
          Site24x7
        </a>
  </td>
  <td align="center" width="150">
        <a>
            <img width="40" src="keep-ui/public/icons/splunk-icon.png" alt="Splunk"/><br/>
          Splunk
        </a>
  </td>
  <td align="center" width="150">
        <a>
            <img width="40" src="keep-ui/public/icons/statuscake-icon.png" alt="StatusCake"/><br/>
          StatusCake
        </a>
  </td>
  <td align="center" width="150">
        <a>
            <img width="40" src="keep-ui/public/icons/sumologic-icon.png" alt="SumoLogic"/><br/>
          SumoLogic
        </a>
  </td>
  <td align="center" width="150">
        <a>
            <img width="40" src="keep-ui/public/icons/thousandeyes-icon.png" alt="SumoLogic"/><br/>
          ThousandEyes
        </a>
  </td>

</tr>
<tr>
    <td align="center" width="150">
        <a>
            <img width="40" src="keep-ui/public/icons/uptimekuma-icon.png" alt="UptimeKuma"/><br/>
          UptimeKuma
        </a>
  </td>
    <td align="center" width="150">
        <a>
            <img width="40" src="keep-ui/public/icons/victorialogs-icon.png" alt="VictoriaLogs"/><br/>
          VictoriaLogs
        </a>
  </td>
    <td align="center" width="150">
        <a>
            <img width="40" src="keep-ui/public/icons/victoriametrics-icon.png" alt="VictoriaMetrics"/><br/>
          VictoriaMetrics
        </a>
  </td>
  <td align="center" width="150">
        <a>
            <img width="40" src="keep-ui/public/icons/wazuh-icon.png" alt="Wazuh"/><br/>
          Wazuh
        </a>
  </td>
  <td align="center" width="150">
        <a>
            <img width="40" src="keep-ui/public/icons/zabbix-icon.png" alt="Zabbix"/><br/>
          Zabbix
        </a>
  </td>
</tr>
</table>

### 数据库与数据仓库

<table>
<tr>
    <td align="center" width="150">
        <a>
            <img width="40" src="keep-ui/public/icons/bigquery-icon.png" alt="BigQuery"/><br/>
            BigQuery
        </a>
    </td>
    <td align="center" width="150">
        <a>
            <img width="40" src="keep-ui/public/icons/clickhouse-icon.png" alt="ClickHouse"/><br/>
            ClickHouse
        </a>
    </td>
    <td align="center" width="150">
        <a>
            <img width="40" src="keep-ui/public/icons/databend-icon.png" alt="Databend"/><br/>
            Databend
        </a>
    </td>
    <td align="center" width="150">
        <a>
            <img width="40" src="keep-ui/public/icons/mongodb-icon.png" alt="MongoDB"/><br/>
            MongoDB
        </a>
    </td>
    <td align="center" width="150">
        <a>
            <img width="40" src="keep-ui/public/icons/mysql-icon.png" alt="MySQL"/><br/>
            MySQL
        </a>
    </td>
    <td align="center" width="150">
        <a>
            <img width="40" src="keep-ui/public/icons/postgres-icon.png" alt="PostgreSQL"/><br/>
            PostgreSQL
        </a>
    </td>
</tr>
<tr>
    <td align="center" width="150">
        <a>
            <img width="40" src="keep-ui/public/icons/snowflake-icon.png" alt="Snowflake"/><br/>
            Snowflake
        </a>
    </td>
</tr>
</table>

### 通信平台

<table>
<tr>
    <td align="center" width="150">
        <a>
            <img width="40" src="keep-ui/public/icons/discord-icon.png" alt="Discord"/><br/>
            Discord
        </a>
    </td>
    <td align="center" width="150">
        <a>
            <img width="40" src="keep-ui/public/icons/google_chat-icon.png" alt="Google Chat"/><br/>
            Google Chat
        </a>
    </td>
    <td align="center" width="150">
        <a>
            <img width="40" src="keep-ui/public/icons/mailgun-icon.png" alt="Mailgun"/><br/>
            Mailgun
        </a>
    </td>
    <td align="center" width="150">
        <a>
            <img width="40" src="keep-ui/public/icons/mattermost-icon.png" alt="Mattermost"/><br/>
            Mattermost
        </a>
    </td>
    <td align="center" width="150">
        <a>
            <img width="40" src="keep-ui/public/icons/ntfy-icon.png" alt="Ntfy.sh"/><br/>
            Ntfy.sh
        </a>
    </td>
  <td align="center" width="150">
        <a>
            <img width="40" src="keep-ui/public/icons/pushover-icon.png" alt="Pushover"/><br/>
            Pushover
        </a>
  </td>
  <td align="center" width="150">
        <a>
            <img width="40" src="keep-ui/public/icons/resend-icon.png" alt="Resend"/><br/>
            Resend
        </a>
  </td>
</tr>
<tr>
  <td align="center" width="150">
      <a>
          <img width="40" src="keep-ui/public/icons/sendgrid-icon.png" alt="SendGrid"/><br/>
          SendGrid
      </a>
  </td>
  <td align="center" width="150">
      <a>
          <img width="40" src="keep-ui/public/icons/slack-icon.png" alt="Slack"/><br/>
          Slack
      </a>
  </td>
  <td align="center" width="150">
      <a>
          <img width="40" src="keep-ui/public/icons/smtp-icon.png" alt="SMTP"/><br/>
          SMTP
      </a>
  </td>
  <td align="center" width="150">
      <a>
          <img width="40" src="keep-ui/public/icons/telegram-icon.png" alt="Telegram"/><br/>
          Telegram
      </a>
  </td>
  <td align="center" width="150">
      <a>
          <img width="40" src="keep-ui/public/icons/twilio-icon.png" alt="Twilio"/><br/>
          Twilio
      </a>
  </td>
  <td align="center" width="150">
      <a>
          <img width="40" src="keep-ui/public/icons/teams-icon.png" alt="Teams"/><br/>
          Teams
      </a>
  </td>
  <td align="center" width="150">
      <a>
          <img width="40" src="keep-ui/public/icons/zoom-icon.png" alt="Zoom"/><br/>
          Zoom
      </a>
  </td>
</tr>
<tr>
  <td align="center" width="150">
      <a>
          <img width="40" src="keep-ui/public/icons/zoom-icon.png" alt="Zoom Chat"/><br/>
          Zoom Chat
      </a>
  </td>
</tr>
</table>

### 事件管理

<table>
  <tr>
      <td align="center" width="150">
          <a>
              <img width="40" src="keep-ui/public/icons/grafana_incident-icon.png" alt="Grafana Incident"/><br/>
              Grafana Incident
          </a>
      </td>
      <td align="center" width="150">
          <a>
              <img width="40" src="keep-ui/public/icons/grafana_oncall-icon.png" alt="Grafana OnCall"/><br/>
              Grafana OnCall
          </a>
      </td>
      <td align="center" width="150">
          <a>
              <img width="40" src="keep-ui/public/icons/ilert-icon.png" alt="Ilert"/><br/>
              Ilert
          </a>
      </td>
      <td align="center" width="150">
          <a>
              <img width="40" src="keep-ui/public/icons/incidentio-icon.png" alt="Incident.io"/><br/>
              Incident.io
          </a>
      </td>
      <td align="center" width="150">
          <a>
              <img width="40" src="keep-ui/public/icons/incidentmanager-icon.png" alt="AWS Incident Manager"/><br/>
              AWS Incident Manager
          </a>
      </td>
      <td align="center" width="150">
          <a>
              <img width="40" src="keep-ui/public/icons/opsgenie-icon.png" alt="OpsGenie"/><br/>
              OpsGenie
          </a>
      </td>
  </tr>
    <tr>
      <td align="center" width="150">
          <a>
              <img width="40" src="keep-ui/public/icons/pagerduty-icon.png" alt="PagerDuty"/><br/>
              PagerDuty
          </a>
      </td>
      <td align="center" width="150">
          <a>
              <img width="40" src="keep-ui/public/icons/pagertree-icon.png" alt="Pagertree"/><br/>
              Pagertree
          </a>
      </td>
      <td align="center" width="150">
          <a>
              <img width="40" src="keep-ui/public/icons/signl4-icon.png" alt="SINGL4"/><br/>
              SINGL4
          </a>
      </td>
      <td align="center" width="150">
          <a>
              <img width="40" src="keep-ui/public/icons/squadcast-icon.png" alt="Squadcast"/><br/>
              Squadcast
          </a>
      </td>
      <td align="center" width="150">
          <a>
              <img width="40" src="keep-ui/public/icons/zenduty-icon.png" alt="Zenduty"/><br/>
              Zenduty
          </a>
      </td>
      <td align="center" width="150">
          <a>
              <img width="40" src="keep-ui/public/icons/flashduty-icon.png" alt="Flashduty"/><br/>
              Flashduty
          </a>
      </td>
  </tr>
</table>

### 工单工具

<table>
<tr>
    <td align="center" width="150">
        <a>
            <img width="40" src="keep-ui/public/icons/asana-icon.png" alt="Asana"/><br/>
            Asana
        </a>
    </td>
    <td align="center" width="150">
        <a>
            <img width="40" src="keep-ui/public/icons/github-icon.png" alt="GitHub"/><br/>
            GitHub
        </a>
    </td>
    <td align="center" width="150">
        <a>
            <img width="40" src="keep-ui/public/icons/gitlab-icon.png" alt="GitLab"/><br/>
            GitLab
        </a>
    </td>
    <td align="center" width="150">
        <a>
            <img width="40" src="keep-ui/public/icons/jira-icon.png" alt="Jira"/><br/>
            Jira
        </a>
    </td>
    <td align="center" width="150">
        <a>
            <img width="40" src="keep-ui/public/icons/linear-icon.png" alt="Linear"/><br/>
            Linear
        </a>
    </td>
    <td align="center" width="150">
        <a>
            <img width="40" src="keep-ui/public/icons/linearb-icon.png" alt="LinearB"/><br/>
            LinearB
        </a>
    </td>
    <td align="center" width="150">
        <a>
            <img width="40" src="keep-ui/public/icons/microsoft-planner-icon.svg" alt="Microsoft Planner"/><br/>
            Microsoft Planner
        </a>
    </td>
</tr>
<tr>
    <td align="center" width="150">
        <a>
            <img width="40" src="keep-ui/public/icons/monday-icon.png" alt="Monday"/><br/>
            Monday
        </a>
    </td>
  <td align="center" width="150">
        <a>
            <img width="40" src="keep-ui/public/icons/redmine-icon.png" alt="Redmine"/><br/>
            Redmine
        </a>
  </td>
  <td align="center" width="150">
      <a>
          <img width="40" src="keep-ui/public/icons/servicenow-icon.png" alt="ServiceNow"/><br/>
          ServiceNow
      </a>
  </td>
  <td align="center" width="150">
      <a>
          <img width="40" src="keep-ui/public/icons/trello-icon.png" alt="Trello"/><br/>
          Trello
      </a>
  </td>
  <td align="center" width="150">
      <a>
          <img width="40" src="keep-ui/public/icons/youtrack-icon.png" alt="YouTrack"/><br/>
          YouTrack
      </a>
  </td>
</tr>
</table>

### 容器编排平台

<table>
<tr>
    <td align="center" width="150">
        <a>
            <img width="40" src="keep-ui/public/icons/aks-icon.png" alt="Azure AKS"/><br/>
            Azure AKS
        </a>
    </td>
    <td align="center" width="150">
        <a>
            <img width="40" src="keep-ui/public/icons/argocd-icon.png" alt="ArgoCD"/><br/>
            ArgoCD
        </a>
    </td>
    <td align="center" width="150">
        <a>
            <img width="40" src="keep-ui/public/icons/fluxcd-icon.png" alt="Flux CD"/><br/>
            Flux
        </a>
    </td>
    <td align="center" width="150">
        <a>
            <img width="40" src="keep-ui/public/icons/gke-icon.png" alt="GKE"/><br/>
            GKE
        </a>
    </td>
    <td align="center" width="150">
        <a>
            <img width="40" src="keep-ui/public/icons/kubernetes-icon.png" alt="Kubernetes"/><br/>
            Kubernetes
        </a>
    </td>
    <td align="center" width="150">
        <a>
            <img width="40" src="keep-ui/public/icons/openshift-icon.png" alt="OpenShift"/><br/>
            OpenShift
        </a>
    </td>
</tr>
</table>

### 数据丰富

<table>
<tr>
<td align="center" width="150">
        <a>
            <img width="40" src="keep-ui/public/icons/bash-icon.png" alt="Bash"/><br/>
            Bash
        </a>
    </td>
    <td align="center" width="150">
        <a>
            <img width="40" src="keep-ui/public/icons/openai-icon.png" alt="OpenAI"/><br/>
            OpenAI
        </a>
    </td>
    <td align="center" width="150">
        <a>
            <img width="40" src="keep-ui/public/icons/python-icon.png" alt="Python"/><br/>
            Python
        </a>
    </td>
    <td align="center" width="150">
        <a>
            <img width="40" src="keep-ui/public/icons/quickchart-icon.png" alt="QuickChart"/><br/>
            QuickChart
        </a>
    </td>
    <td align="center" width="150">
        <a>
            <img width="40" src="keep-ui/public/icons/ssh-icon.png" alt="SSH"/><br/>
            SSH
        </a>
    </td>
    <td align="center" width="150">
        <a>
            <img width="40" src="keep-ui/public/icons/webhook-icon.png" alt="Webhook"/><br/>
            Webhook
        </a>
    </td>
</tr>
</table>

### 工作流编排

<table>
<tr>
    <td align="center" width="150">
        <a>
            <img width="40" src="keep-ui/public/icons/airflow-icon.png" alt="Airflow"/><br/>
            Airflow
        </a>
    </td>
</tr>
</table>

### 队列

<table>
<tr>
    <td align="center" width="150">
        <a>
            <img width="40" src="keep-ui/public/icons/amazonsqs-icon.png" alt="AmazonSQS"/><br/>
            Amazon SQS
        </a>
    </td>
    <td align="center" width="150">
        <a>
            <img width="40" src="keep-ui/public/icons/kafka-icon.png" alt="Kafka"/><br/>
            Kafka
        </a>
    </td>
</tr>
</table>

## 工作流

Keep 是为你的监控工具提供的 GitHub Actions。

Keep 工作流是一个声明式的 YAML 文件，自动化你的告警与事件管理。每个工作流包含：

- **触发器** - 启动工作流的事件（告警、事件、计划或手动）
- **步骤** - 读取或拉取数据（丰富、上下文）
- **操作** - 执行动作（更新工单、发送通知、重启服务器）

下面是一个简单的工作流，在 `payments` 与 `api` 服务中为每个来自 `sentry` 的 `critical` 告警创建 Jira 工单。

更多工作流请见 `examples/workflows` 目录。

```yaml
workflow:
  id: sentry-alerts
  description: create ticket alerts for critical alerts from sentry
  triggers:
    - type: alert
      # customize the filter to run only on critical alert from sentry
      filters:
        - key: source
          value: sentry
        - key: severity
          value: critical
        # regex to match specific services
        - key: service
          value: r"(payments|ftp)"
  actions:
    - name: send-slack-message-team-payments
      # if the alert is on the payments service, slack the payments team
      if: "'{{ alert.service }}' == 'payments'"
      provider:
        type: slack
        # control which Slack configuration you want to use
        config: " {{ providers.team-payments-slack }} "
        # customize the alert message with context from {{ alert }} or any other {{ step }}
        with:
          message: |
            "A new alert from Sentry: Alert: {{ alert.name }} - {{ alert.description }}
            {{ alert}}"
    - name: create-jira-ticket-oncall-board
      # control the workflow flow with "if" and "foreach" statements
      if: "'{{ alert.service }}' == 'ftp' and not '{{ alert.ticket_id }}'"
      provider:
        type: jira
        config: " {{ providers.jira }} "
        with:
          board_name: "Oncall Board"
          custom_fields:
            customfield_10201: "Critical"
          issuetype: "Task"
          # customize the summary
          summary: "{{ alert.name }} - {{ alert.description }} (created by Keep)"
          description: |
            "This ticket was created by Keep.
            Please check the alert details below:
            {code:json} {{ alert }} {code}"
          # enrich the alerts with more context. from now on, the alert will be assigned with the ticket id, type and url
          enrich_alert:
            - key: ticket_type
              value: jira
            - key: ticket_id
              value: results.issue.key
            - key: ticket_url
              value: results.ticket_url
```

## 企业就绪

- **以开发者为先** - 现代 REST API、原生 SDK 与全面的文档，实现无缝集成
- **企业安全** - 完整认证支持（SSO、SAML、OIDC、LDAP），配合细粒度访问控制（RBAC、ABAC）与团队管理
- **灵活部署** - 可在本地或隔离环境中部署，架构与云无关
- **生产级规模** - 支持横向扩展的高可用、性能验证基础设施

## 入门指南

最简单的启动方式是 Docker Compose（默认 NO_AUTH 免认证、SQLite 存储，适合内网试用）：

```bash
mkdir gengfu && cd gengfu
curl -O https://raw.githubusercontent.com/fadewalk/gengfu/main/docker-compose.yml
docker compose up -d
```

打开 `http://localhost:4000` 即可使用（API 在 `http://localhost:8080`）。

**生产环境建议**：

- 认证：设置 `AUTH_TYPE=LDAP` 并填入 `LDAP_URL` / `LDAP_BASE_DN` 等环境变量对接企业 AD/OpenLDAP（所有变量见 compose 文件内注释）
- 数据库：注释 SQLite 连接串，启用 MySQL 段
- 集成目录默认隐藏了 54 个海外 SaaS（`KEEP_DEFAULT_HIDDEN_PROVIDERS` 可整体覆盖），钉钉、企业微信、飞书、Zabbix、Prometheus、Grafana 等国内常用集成开箱可见

## 入门指南（源码开发）

Keep 可在多种环境与配置中运行。最简单的启动方式是使用 Docker Compose。

```bash
cd deploy/docker
docker compose up -d
```

## 致谢

本项目基于 [Keep](https://github.com/keephq/keep)（MIT License）二次开发，感谢 [KeepHQ](https://github.com/keephq) 团队与开源社区的贡献。上游的持续演进是本项目的地基，我们会定期同步上游更新，并把有普适价值的改动回馈上游。
