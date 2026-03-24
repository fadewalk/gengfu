"""
WebsocketProvider 实现了一个简单的 WebSocket 提供商。
"""

import pydantic
import websocket
import websocket._exceptions

from keep.api.i18n import t
from keep.contextmanager.contextmanager import ContextManager
from keep.providers.base.base_provider import BaseProvider
from keep.providers.models.provider_config import ProviderConfig


@pydantic.dataclasses.dataclass
class WebsocketProviderAuthConfig:
    pass


class WebsocketProvider(BaseProvider):
    """通过 WebSocket 获取数据富化告警。"""
    provider_description = t("Enrich alerts with data from a websocket.")

    def __init__(
        self, context_manager: ContextManager, provider_id: str, config: ProviderConfig
    ):
        super().__init__(context_manager, provider_id, config)
        self.ws = None

    def validate_config(self):
        self.authentication_config = WebsocketProviderAuthConfig(
            **self.config.authentication
        )

    def _query(
        self,
        socket_url: str,
        timeout: int | None = None,
        data: str | None = None,
        **kwargs: dict
    ) -> dict:
        """
        Query a websocket endpoint.

        Args:
            socket_url (str): The websocket URL to query.
            timeout (int | None, optional): Connection Timeout. Defaults to None.
            data (str | None, optional): Data to send through the websocket. Defaults to None.

        Returns:
            str: First received bytes from the websocket.
        """
        try:
            self.ws = websocket.create_connection(socket_url, timeout=timeout)
            received = self.ws.recv()
            if data:
                self.ws.send(data)
            return {"connection": True, "data": received, "error": None}
        except websocket._exceptions.WebSocketException as e:
            self.logger.exception("Failed to connect to websocket")
            return {"connection": False, "data": None, "error": e}

    def dispose(self):
        """
        Dispose of the websocket connection.
        """
        try:
            self.ws.close()
        except Exception:
            self.logger.warning("Failed to close websocket connection")


if __name__ == "__main__":
    # Initalize the provider and provider config
    config = ProviderConfig(
        id="websocket-test",
        authentication={},
    )
    context_manager = ContextManager(
        tenant_id="singletenant",
        workflow_id="test",
    )
    provider = WebsocketProvider(
        context_manager, provider_id="websocket", config=config
    )
    response = provider.query(socket_url="ws://echo.websockets.events")
    print(response)
