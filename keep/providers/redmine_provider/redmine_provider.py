"""
RedmineProvider 实现了 BaseProvider 接口，用于处理 Redmine 议题。
"""

import dataclasses

import pydantic
import requests
from requests import HTTPError

from keep.api.i18n import t
from keep.contextmanager.contextmanager import ContextManager
from keep.providers.base.base_provider import BaseProvider
from keep.providers.models.provider_config import ProviderConfig, ProviderScope


@pydantic.dataclasses.dataclass
class RedmineProviderAuthConfig:
    """Redmine 认证配置。"""

    host: pydantic.AnyHttpUrl = dataclasses.field(
        metadata={
            "required": True,
            "description": t("Redmine Host"),
            "sensitive": False,
            "hint": "http://localhost:8080",
            "validation": "any_http_url",
        }
    )

    api_access_key: str = dataclasses.field(
        metadata={
            "required": True,
            "description": t("Redmine API Access key"),
            "sensitive": True,
            "documentation_url": "https://www.redmine.org/projects/redmine/wiki/rest_api#Authentication",
        }
    )

    ticket_creation_url: str = dataclasses.field(
        metadata={
            "required": False,
            "description": t("URL for creating new tickets"),
            "sensitive": False,
            "hint": "http://localhost:8080/issues/new",
        },
        default="",
    )


class RedmineProvider(BaseProvider):
    """使用 Redmine 工单富化告警。"""
    provider_description = t("Enrich alerts with Redmine tickets.")

    PROVIDER_DISPLAY_NAME = "Redmine"
    PROVIDER_SCOPES = [
        ProviderScope(
            name="authenticated",
            description=t("Authenticated with Redmine API"),
            mandatory=True,
            alias=t("Redmine API Access Key"),
        ),
    ]
    PROVIDER_TAGS = ["ticketing"]
    PROVIDER_CATEGORY = ["Ticketing"]

    def __init__(
        self, context_manager: ContextManager, provider_id: str, config: ProviderConfig
    ):
        self._host = None
        super().__init__(context_manager, provider_id, config)

    def validate_scopes(self):
        """
        Validate that the provider has the required scopes.
        """

        # first, validate user/api token are correct:
        resp = requests.get(
            f"{self.__redmine_url}/users/current.json",
            headers=self.__get_headers(),
        )
        try:
            resp.raise_for_status()
            if resp.status_code == 200:
                scopes = {"authenticated": True}
            else:
                self.logger.error(
                    t("Failed to validate scope for {provider_id}", provider_id=self.provider_id),
                    extra=resp.json(),
                )
                scopes = {
                    "authenticated": {
                        "status_code": resp.status_code,
                        "error": resp.json(),
                    }
                }
        except HTTPError as e:
            self.logger.error(
                t("HTTPError while validating scope for {provider_id}", provider_id=self.provider_id),
                extra={"error": str(e)},
            )
            scopes = {
                "authenticated": {"status_code": resp.status_code, "error": str(e)}
            }

        return scopes

    def validate_config(self):
        self.authentication_config = RedmineProviderAuthConfig(
            **self.config.authentication
        )

    @property
    def __redmine_url(self):
        # if not the first time, return the cached host
        if self._host:
            return self._host.rstrip("/")

        # if the user explicitly supplied a host with http/https, use it
        if self.authentication_config.host.startswith(
            "http://"
        ) or self.authentication_config.host.startswith("https://"):
            self._host = self.authentication_config.host
            return self.authentication_config.host.rstrip("/")

        # otherwise, try to use https:
        try:
            requests.get(
                f"https://{self.authentication_config.host}",
                verify=False,
            )
            self.logger.debug("Using https")
            self._host = f"https://{self.authentication_config.host}"
            return self._host.rstrip("/")
        except requests.exceptions.SSLError:
            self.logger.debug("Using http")
            self._host = f"http://{self.authentication_config.host}"
            return self._host.rstrip("/")
        # should happen only if the user supplied invalid host, so just let validate_config fail
        except Exception:
            return self.authentication_config.host.rstrip("/")

    def dispose(self):
        """
        No need to dispose of anything, so just do nothing.
        """
        pass

    def __get_headers(self):
        """
        Helper method to build the auth header for redmine api requests.
        """
        return {
            "Content-Type": "application/json",
            "X-Redmine-API-Key": self.authentication_config.api_access_key,
        }

    def __build_payload_from_kwargs(self, kwargs: dict):
        params = dict()
        for param in kwargs:
            if isinstance(kwargs[param], list):
                params[param] = ",".join(kwargs[param])
            else:
                params[param] = kwargs[param]
        return params

    def _notify(
        self,
        project_id: str,
        subject: str,
        priority_id: str,
        description: str = "",
        **kwargs: dict,
    ):
        self.logger.info("Creating an issue in redmine")
        payload = self.__build_payload_from_kwargs(
            kwargs={
                **kwargs,
                "subject": subject,
                "description": description,
                "project_id": project_id,
                "priority_id": priority_id,
            }
        )
        resp = requests.post(
            f"{self.__redmine_url}/issues.json",
            headers=self.__get_headers(),
            json={"issue": payload},
        )
        try:
            resp.raise_for_status()
        except HTTPError as e:
            self.logger.error(t("Error While creating Redmine Issue"))
            raise Exception(t("Failed to create Redmine issue: {error}", error=str(e)))
        self.logger.info(
            t("Successfully created a Redmine Issue"),
            extra={"status_code": resp.status_code},
        )
        return resp.json()
