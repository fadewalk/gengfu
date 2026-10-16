"""
WecomProvider 实现了 BaseProvider 接口，用于发送企业微信群机器人消息。

通过企业微信群机器人 Webhook 把告警推送到企业微信群。
注意：企业微信机器人有频控限制（每个机器人每分钟约 20 条）。
"""

import dataclasses
from typing import Optional

import pydantic
import requests

from keep.api.i18n import t
from keep.contextmanager.contextmanager import ContextManager
from keep.exceptions.provider_exception import ProviderException
from keep.providers.base.base_provider import BaseProvider
from keep.providers.models.provider_config import ProviderConfig, ProviderScope

WECOM_ROBOT_SEND_URL = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send"


@pydantic.dataclasses.dataclass
class WecomProviderAuthConfig:
    """企业微信群机器人认证配置。"""

    key: str = dataclasses.field(
        metadata={
            "required": True,
            "description": t("Robot webhook key (the key= parameter of the webhook URL)"),
            "sensitive": True,
        }
    )


class WecomProvider(BaseProvider):
    """发送告警消息到企业微信群。"""

    provider_description = t("Send alert message to a WeCom group robot.")
    PROVIDER_DISPLAY_NAME = "WeCom"
    PROVIDER_CATEGORY = ["Collaboration"]

    PROVIDER_SCOPES = [
        ProviderScope(
            name="robot_send",
            description=t("Send messages to the WeCom group via robot webhook"),
        )
    ]

    def __init__(
        self, context_manager: ContextManager, provider_id: str, config: ProviderConfig
    ):
        super().__init__(context_manager, provider_id, config)

    def validate_config(self):
        self.authentication_config = WecomProviderAuthConfig(
            **self.config.authentication
        )

    def dispose(self):
        """无需释放资源。"""
        pass

    @staticmethod
    def _build_text_payload(
        message: str,
        mentioned_mobiles: Optional[list[str]] = None,
        at_all: bool = False,
    ) -> dict:
        """构造企业微信 text 消息体。@ 提醒只在 text 类型下生效。"""
        mentioned_mobile_list: list = []
        if at_all:
            mentioned_mobile_list.append("@all")
        if mentioned_mobiles:
            mentioned_mobile_list.extend(mentioned_mobiles)
        return {
            "msgtype": "text",
            "text": {
                "content": message,
                **({"mentioned_mobile_list": mentioned_mobile_list} if mentioned_mobile_list else {}),
            },
        }

    @staticmethod
    def _build_markdown_payload(message: str) -> dict:
        """构造企业微信 markdown 消息体。"""
        return {"msgtype": "markdown", "markdown": {"content": message}}

    def _notify(
        self,
        message: str = "",
        title: str = "",
        at_mobiles: Optional[list[str]] = None,
        at_all: bool = False,
        **kwargs: dict,
    ):
        """
        通过企业微信群机器人 Webhook 发送消息。
        https://developer.work.weixin.qq.com/document/path/91770

        Args:
            message (str): 消息正文。有 @ 需求时为纯文本，否则支持企业微信 Markdown 子集
            title (str): 消息标题，非空时作为一级标题拼在正文前（仅 markdown 生效）
            at_mobiles (list[str], optional): 需要 @ 的成员手机号列表（仅 text 消息生效）
            at_all (bool): 是否 @ 所有人，默认 False（仅 text 消息生效）
        """
        self.logger.debug("Notifying alert message to WeCom")

        if not message:
            raise ProviderException(
                t(
                    "{provider} failed to notify: message is required",
                    provider=self.__class__.__name__,
                )
            )

        # @ 提醒只在 text 消息类型下生效；有 @ 需求时降级为纯文本
        if at_mobiles or at_all:
            payload = self._build_text_payload(
                message=message, mentioned_mobiles=at_mobiles, at_all=at_all
            )
        else:
            content = f"## {title}\n{message}" if title else message
            payload = self._build_markdown_payload(message=content)

        url = f"{WECOM_ROBOT_SEND_URL}?key={self.authentication_config.key}"
        try:
            response = requests.post(url, json=payload, timeout=30)
            response.raise_for_status()
            result = response.json()
        except Exception as e:
            raise ProviderException(
                t(
                    "{provider} failed to notify alert message to WeCom: {error}",
                    provider=self.__class__.__name__,
                    error=str(e),
                )
            )

        if result.get("errcode") != 0:
            raise ProviderException(
                t(
                    "{provider} WeCom API error: {errcode} {errmsg}",
                    provider=self.__class__.__name__,
                    errcode=result.get("errcode"),
                    errmsg=result.get("errmsg"),
                )
            )

        self.logger.debug("Alert message notified to WeCom")
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
        description="WeCom Provider",
        authentication={"key": os.environ.get("WECOM_KEY")},
    )
    provider = WecomProvider(context_manager, provider_id="wecom-test", config=config)
    provider.notify(
        message="**CPU 使用率超过 90%**\n> 环境: production",
        title="更夫告警",
    )
