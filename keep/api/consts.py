import os

from dotenv import find_dotenv, load_dotenv

from keep.api.models.db.preset import PresetDto, StaticPresetsId

load_dotenv(find_dotenv())
RUNNING_IN_CLOUD_RUN = os.environ.get("K_SERVICE") is not None
PROVIDER_PULL_INTERVAL_MINUTE = int(
    os.environ.get("KEEP_PULL_INTERVAL", 10080)
)  # maximum once a week
STATIC_PRESETS = {
    "feed": PresetDto(
        id=StaticPresetsId.FEED_PRESET_ID.value,
        name="feed",
        options=[
            {"label": "CEL", "value": ""},
            {
                "label": "SQL",
                "value": {"sql": "", "params": {}},
            },
        ],
        created_by=None,
        is_private=False,
        is_noisy=False,
        should_do_noise_now=False,
        static=True,
        tags=[],
    )
}
MAINTENANCE_WINDOW_ALERT_STRATEGY = os.environ.get(
    "MAINTENANCE_WINDOW_STRATEGY", "default"
)  # recover_previous_status or default
WATCHER_LAPSED_TIME = int(os.environ.get("KEEP_WATCHER_LAPSED_TIME", 60))  # in seconds
###
# Set ARQ_TASK_POOL_TO_EXECUTE to "none", "all", "basic_processing" or "ai"
# to split the tasks between the workers.
###

KEEP_ARQ_TASK_POOL_ALL = "all"  # All arq workers enabled for this service
KEEP_ARQ_TASK_POOL_BASIC_PROCESSING = "basic_processing"  # Everything except AI
# Define queues for different task types
KEEP_ARQ_QUEUE_BASIC = "basic_processing"
KEEP_ARQ_QUEUE_WORKFLOWS = "workflows"
KEEP_ARQ_QUEUE_MAINTENANCE = "maintenance"

REDIS = os.environ.get("REDIS", "false") == "true"

if REDIS:
    KEEP_ARQ_TASK_POOL = os.environ.get("KEEP_ARQ_TASK_POOL", KEEP_ARQ_TASK_POOL_ALL)
else:
    KEEP_ARQ_TASK_POOL = os.environ.get("KEEP_ARQ_TASK_POOL", None)

OPENAI_MODEL_NAME = os.environ.get("OPENAI_MODEL_NAME", "gpt-4o-2024-08-06")
OPENAI_BASE_URL = os.environ.get("OPENAI_BASE_URL", None)

# DEPRECATED: AI model config is now managed via database (Settings > AI Configuration).
# The env vars below are kept only for backward compatibility during migration.

KEEP_CORRELATION_ENABLED = os.environ.get("KEEP_CORRELATION_ENABLED", "true") == "true"

FINGERPRINT_PAYLOAD_LIMIT = 100


def fingerprints_for_poll_payload(fingerprints: list[str]) -> list[str]:
    if len(fingerprints) <= FINGERPRINT_PAYLOAD_LIMIT:
        return fingerprints
    return []


# ============================================================
# 更夫出厂默认隐藏的 provider 清单（海外 SaaS / 国内不可用）
#
# 设计：
# - 租户未自定义 hidden_providers 时生效（设置页保存过任何列表后即完全以租户配置为准）
# - KEEP_DEFAULT_HIDDEN_PROVIDERS 环境变量可整体覆盖：置空串 = 关闭裁剪显示全部，
#   逗号分隔 = 自定义默认隐藏清单
# - 被隐藏的 provider 仍可正常使用（工作流里 type 直接引用不受影响），只是
#   集成目录默认不展示；设置页「提供商可见性」可随时找回
# ============================================================

GENGFU_DEFAULT_HIDDEN_PROVIDERS = [
    # 海外告警/事件管理 SaaS
    "pagerduty", "opsgenie", "ilert", "incidentio", "incidentmanager",
    "pagertree", "squadcast", "signl4", "zenduty", "grafana_incident",
    # 海外 IM / 通知
    "slack", "teams", "discord", "telegram", "google_chat",
    "zoom", "zoom_chat", "twilio", "mailgun", "sendgrid", "resend", "pushover",
    # 海外可观测性 SaaS
    "datadog", "dynatrace", "newrelic", "appdynamics", "sumologic",
    "coralogix", "axiom", "dash0", "rollbar", "signalfx",
    # 海外拨测/可用性 SaaS
    "checkly", "pingdom", "statuscake", "thousandeyes", "site24x7",
    # 海外工单/协作 SaaS
    "jira", "servicenow", "asana", "trello", "monday", "planner", "linear", "linearb",
    # 海外云 / 云上 SaaS（中国大陆不可达或无中国区）
    "auth0", "azuremonitoring", "gcpmonitoring", "aks", "gke",
    "opensearchserverless", "bigquery", "snowflake", "salesforce", "posthog",
]


def get_default_hidden_providers() -> list[str]:
    """返回出厂默认隐藏的 provider 类型列表，支持环境变量整体覆盖。

    - KEEP_DEFAULT_HIDDEN_PROVIDERS 未设置：返回内置海外 SaaS 清单
    - 置为空串：返回 []（关闭出厂裁剪，显示全部）
    - 逗号分隔值：返回自定义清单
    """
    raw = os.environ.get("KEEP_DEFAULT_HIDDEN_PROVIDERS")
    if raw is None:
        return list(GENGFU_DEFAULT_HIDDEN_PROVIDERS)
    raw = raw.strip()
    if not raw:
        return []
    return [item.strip() for item in raw.split(",") if item.strip()]
