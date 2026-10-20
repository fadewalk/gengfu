"""
DingtalkProvider 实现了 BaseProvider 接口，用于发送钉钉群机器人消息。

通过钉钉自定义机器人（群 Webhook）把告警推送到钉钉群，支持加签安全设置。
"""

import dataclasses
import hashlib
import hmac
import base64
import urllib.parse
from typing import Optional

import pydantic
import requests

from keep.api.i18n import t
from keep.contextmanager.contextmanager import ContextManager
from keep.exceptions.provider_exception import ProviderException
from keep.providers.base.base_provider import BaseProvider
from keep.providers.models.provider_config import ProviderConfig, ProviderScope

DINGTALK_ROBOT_SEND_URL = "https://oapi.dingtalk.com/robot/send"


@pydantic.dataclasses.dataclass
class DingtalkProviderAuthConfig:
    """钉钉群机器人认证配置。"""

    access_token: str = dataclasses.field(
        metadata={
            "required": True,
            "description": t("Robot webhook access_token (from the webhook URL)"),
            "sensitive": True,
        }
    )
    secret: Optional[str] = dataclasses.field(
        default=None,
        metadata={
            "required": False,
            "description": t(
                "Sign secret (starts with SEC) if the robot uses the signed security mode"
            ),
            "sensitive": True,
            "hint": "SEC...",
        },
    )



def _normalize_at_list(value) -> list:
    """at 参数归一化：接受 list 或逗号分隔字符串（工作流渲染产物）。"""
    if value is None:
        return []
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    return list(value)

class DingtalkProvider(BaseProvider):
    """发送告警消息到钉钉群。"""

    provider_description = t("Send alert message to a DingTalk group robot.")
    PROVIDER_DISPLAY_NAME = "DingTalk"
    PROVIDER_CATEGORY = ["Collaboration"]

    PROVIDER_SCOPES = [
        ProviderScope(
            name="robot_send",
            description=t("Send messages to the DingTalk group via robot webhook"),
        )
    ]

    def __init__(
        self, context_manager: ContextManager, provider_id: str, config: ProviderConfig
    ):
        super().__init__(context_manager, provider_id, config)

    def validate_config(self):
        self.authentication_config = DingtalkProviderAuthConfig(
            **self.config.authentication
        )

    def dispose(self):
        """无需释放资源。"""
        pass

    def _gen_signed_url(self, timestamp: int) -> str:
        """按钉钉加签规则生成带 timestamp 与 sign 参数的 webhook URL。

        sign = urlencoded(base64(hmac_sha256(key=secret, msg=f"{timestamp}\\n{secret}")))
        """
        secret = self.authentication_config.secret
        string_to_sign = f"{timestamp}\n{secret}"
        hmac_code = hmac.new(
            secret.encode("utf-8"),
            string_to_sign.encode("utf-8"),
            digestmod=hashlib.sha256,
        ).digest()
        sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))
        return f"{DINGTALK_ROBOT_SEND_URL}?access_token={self.authentication_config.access_token}&timestamp={timestamp}&sign={sign}"

    @staticmethod
    def _build_markdown_payload(
        message: str,
        title: str,
        at_mobiles: Optional[list[str]] = None,
        at_all: bool = False,
        link_url: Optional[str] = None,
        link_text: str = "",
    ) -> dict:
        """构造钉钉 markdown 消息体。"""
        at_section: dict = {"isAtAll": at_all}
        at_mobiles = _normalize_at_list(at_mobiles)
        if at_mobiles:
            at_section["atMobiles"] = at_mobiles
        if link_url:
            message = f"{message}\n\n**[{link_text or t('View details')}]({link_url})**"
        return {
            "msgtype": "markdown",
            "markdown": {"title": title, "text": message},
            "at": at_section,
        }

    def _notify(
        self,
        message: str = "",
        title: str = "",
        at_mobiles: Optional[list[str]] = None,
        at_all: bool = False,
        link_url: Optional[str] = None,
        link_text: str = "",
        **kwargs: dict,
    ):
        """
        通过钉钉群机器人 Webhook 发送 markdown 消息。
        https://open.dingtalk.com/document/orgapp/custom-robots-send-group-messages

        Args:
            message (str): 消息正文（markdown）
            title (str): 消息标题，会话列表中展示，默认「更夫告警」
            at_mobiles (list[str], optional): 需要 @ 的手机号列表
            at_all (bool): 是否 @ 所有人，默认 False
            link_url (str, optional): 「查看详情」链接（如更夫事件页地址）
            link_text (str, optional): 链接文字，默认「查看详情」
        """
        self.logger.debug("Notifying alert message to DingTalk")

        if not message:
            raise ProviderException(
                t(
                    "{provider} failed to notify: message is required",
                    provider=self.__class__.__name__,
                )
            )

        if self.authentication_config.secret:
            import time

            url = self._gen_signed_url(int(time.time() * 1000))
        else:
            url = f"{DINGTALK_ROBOT_SEND_URL}?access_token={self.authentication_config.access_token}"

        payload = self._build_markdown_payload(
            message=message,
            title=title or t("Gengfu Alert"),
            at_mobiles=at_mobiles,
            at_all=at_all,
            link_url=link_url,
            link_text=link_text,
        )

        try:
            response = requests.post(url, json=payload, timeout=30)
            response.raise_for_status()
            result = response.json()
        except Exception as e:
            raise ProviderException(
                t(
                    "{provider} failed to notify alert message to DingTalk: {error}",
                    provider=self.__class__.__name__,
                    error=str(e),
                )
            )

        # 钉钉返回 200 但业务失败时 errcode != 0（如关键词不匹配、被限流）
        if result.get("errcode") != 0:
            raise ProviderException(
                t(
                    "{provider} DingTalk API error: {errcode} {errmsg}",
                    provider=self.__class__.__name__,
                    errcode=result.get("errcode"),
                    errmsg=result.get("errmsg"),
                )
            )

        self.logger.debug("Alert message notified to DingTalk")
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
        description="DingTalk Provider",
        authentication={
            "access_token": os.environ.get("DINGTALK_ACCESS_TOKEN"),
            "secret": os.environ.get("DINGTALK_SECRET"),
        },
    )
    provider = DingtalkProvider(
        context_manager, provider_id="dingtalk-test", config=config
    )
    provider.notify(
        message="#### 更夫告警\n\n> CPU 使用率超过 90%\n\n- 环境: production",
        title="CPU 告警",
        at_mobiles=["13800138000"],
    )
