"""
FeishuProvider 实现了 BaseProvider 接口，用于发送飞书群机器人消息。

通过飞书自定义机器人（群 Webhook）以卡片消息推送告警，支持签名校验安全设置。
"""

import base64
import dataclasses
import hashlib
import hmac
import time
from typing import Optional

import pydantic
import requests

from keep.api.i18n import t
from keep.contextmanager.contextmanager import ContextManager
from keep.exceptions.provider_exception import ProviderException
from keep.providers.base.base_provider import BaseProvider
from keep.providers.models.provider_config import ProviderConfig, ProviderScope

FEISHU_ROBOT_SEND_URL = "https://open.feishu.cn/open-apis/bot/v2/hook"
# 卡片 header template 支持的告警色
_HEADER_TEMPLATES = {"blue", "wathet", "turquoise", "green", "yellow", "orange", "red", "carmine", "violet"}


@pydantic.dataclasses.dataclass
class FeishuProviderAuthConfig:
    """飞书自定义机器人认证配置。"""

    hook_token: str = dataclasses.field(
        metadata={
            "required": True,
            "description": t("Robot hook token (the path segment after /bot/v2/hook/)"),
            "sensitive": True,
        }
    )
    secret: Optional[str] = dataclasses.field(
        default=None,
        metadata={
            "required": False,
            "description": t("Sign secret if the robot uses signature verification"),
            "sensitive": True,
        },
    )



def _normalize_at_list(value) -> list:
    """at 参数归一化：接受 list 或逗号分隔字符串（工作流渲染产物）。"""
    if value is None:
        return []
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    return list(value)

class FeishuProvider(BaseProvider):
    """发送告警消息到飞书群。"""

    provider_description = t("Send alert message to a Feishu group robot.")
    PROVIDER_DISPLAY_NAME = "Feishu"
    PROVIDER_CATEGORY = ["Collaboration"]

    PROVIDER_SCOPES = [
        ProviderScope(
            name="robot_send",
            description=t("Send messages to the Feishu group via robot webhook"),
        )
    ]

    def __init__(
        self, context_manager: ContextManager, provider_id: str, config: ProviderConfig
    ):
        super().__init__(context_manager, provider_id, config)

    def validate_config(self):
        self.authentication_config = FeishuProviderAuthConfig(
            **self.config.authentication
        )

    def dispose(self):
        """无需释放资源。"""
        pass

    @staticmethod
    def _gen_sign(timestamp: int, secret: str) -> str:
        """按飞书签名规则生成 sign。

        与钉钉不同：飞书把 f"{timestamp}\\n{secret}" 整体作为 HMAC-SHA256 的 key，
        message 为空，再 base64。
        """
        string_to_sign = f"{timestamp}\n{secret}"
        hmac_code = hmac.new(string_to_sign.encode("utf-8"), digestmod=hashlib.sha256).digest()
        return base64.b64encode(hmac_code).decode("utf-8")

    @staticmethod
    def _build_card_payload(
        message: str,
        title: str,
        color: str = "blue",
        at_all: bool = False,
        at_emails: Optional[list[str]] = None,
        link_url: Optional[str] = None,
        link_text: str = "",
    ) -> dict:
        """构造飞书交互卡片消息体，正文使用 markdown 元素。"""
        content = message
        at_prefixes = []
        if at_all:
            at_prefixes.append("<at id=all></at>")
        # 飞书卡片 lark_md 支持按邮箱 @ 人，无需开放平台 user_id 映射
        for email in _normalize_at_list(at_emails):
            at_prefixes.append(f'<at email="{email}"></at>')
        if at_prefixes:
            content = f"{' '.join(at_prefixes)}\n{content}"
        elements = [{"tag": "markdown", "content": content}]
        if link_url:
            elements.append(
                {
                    "tag": "action",
                    "actions": [
                        {
                            "tag": "button",
                            "text": {"tag": "plain_text", "content": link_text or t("View details")},
                            "type": "primary",
                            "url": link_url,
                        }
                    ],
                }
            )
        return {
            "msg_type": "interactive",
            "card": {
                "header": {
                    "title": {"tag": "plain_text", "content": title},
                    "template": color if color in _HEADER_TEMPLATES else "blue",
                },
                "elements": elements,
            },
        }

    def _notify(
        self,
        message: str = "",
        title: str = "",
        color: str = "blue",
        at_all: bool = False,
        at_emails: Optional[list[str]] = None,
        link_url: Optional[str] = None,
        link_text: str = "",
        **kwargs: dict,
    ):
        """
        通过飞书自定义机器人 Webhook 发送卡片消息。
        https://open.feishu.cn/document/client-docs/bot-v3/add-custom-bot

        Args:
            message (str): 消息正文，支持飞书卡片 markdown 语法
            title (str): 卡片标题，默认「更夫告警」
            color (str): 卡片头部分色，默认 blue；告警严重度可用 red/orange/yellow
            at_all (bool): 是否 @ 所有人，默认 False
            at_emails (list[str], optional): 需要 @ 的成员飞书邮箱列表（卡片内按邮箱 @，无需开放平台映射）
            link_url (str, optional): 「查看详情」按钮跳转地址（如更夫事件页）
            link_text (str, optional): 按钮文字，默认「查看详情」
        """
        self.logger.debug("Notifying alert message to Feishu")

        if not message:
            raise ProviderException(
                t(
                    "{provider} failed to notify: message is required",
                    provider=self.__class__.__name__,
                )
            )

        payload = self._build_card_payload(
            message=message,
            title=title or t("Gengfu Alert"),
            color=color,
            at_all=at_all,
            at_emails=at_emails,
            link_url=link_url,
            link_text=link_text,
        )

        url = f"{FEISHU_ROBOT_SEND_URL}/{self.authentication_config.hook_token}"
        if self.authentication_config.secret:
            timestamp = int(time.time())
            payload["timestamp"] = timestamp
            payload["sign"] = self._gen_sign(timestamp, self.authentication_config.secret)

        try:
            response = requests.post(url, json=payload, timeout=30)
            response.raise_for_status()
            result = response.json()
        except Exception as e:
            raise ProviderException(
                t(
                    "{provider} failed to notify alert message to Feishu: {error}",
                    provider=self.__class__.__name__,
                    error=str(e),
                )
            )

        # 新版接口返回 {"code":0,...}；兼容旧版 StatusCode 口径
        code = result.get("code", result.get("StatusCode", 0))
        if code != 0:
            raise ProviderException(
                t(
                    "{provider} Feishu API error: {code} {msg}",
                    provider=self.__class__.__name__,
                    code=code,
                    msg=result.get("msg") or result.get("StatusMessage"),
                )
            )

        self.logger.debug("Alert message notified to Feishu")
        return result


if __name__ == "__main__":
    import logging
    import os

    logging.basicConfig(level=logging.DEBUG, handlers=[logging.StreamHandler()])
    context_manager = ContextManager(
        tenant_id="singletenant",
        workflow_id="test",
    )

    config = ProviderConfig(
        description="Feishu Provider",
        authentication={
            "hook_token": os.environ.get("FEISHU_HOOK_TOKEN"),
            "secret": os.environ.get("FEISHU_SECRET"),
        },
    )
    provider = FeishuProvider(
        context_manager, provider_id="feishu-test", config=config
    )
    provider.notify(
        message="**CPU 使用率超过 90%**\n- 环境: production",
        title="更夫告警",
        color="red",
    )
