import json
import dataclasses
import logging
from typing import Optional
import pydantic
from openai import OpenAI
from openai import APIStatusError

from keep.api.i18n import t
from keep.contextmanager.contextmanager import ContextManager
from keep.providers.base.base_provider import BaseProvider
from keep.providers.models.provider_config import ProviderConfig

logger = logging.getLogger(__name__)


@pydantic.dataclasses.dataclass
class CustomaiProviderAuthConfig:
    api_key: str = dataclasses.field(
        metadata={
            "required": True,
            "description": t("API Key for the AI service"),
            "sensitive": True,
        },
    )
    base_url: str = dataclasses.field(
        metadata={
            "required": True,
            "description": t("Base URL of the AI API (e.g., https://api.openai.com/v1)"),
            "validation": "any_http_url",
        },
    )
    models: str = dataclasses.field(
        metadata={
            "required": False,
            "description": t("Comma-separated list of model IDs (e.g., gpt-4, gpt-3.5-turbo)"),
            "hint": t("First model will be used as default. Models will be tried in order for failover."),
        },
        default="gpt-4o-mini",
    )
    timeout: int = dataclasses.field(
        metadata={
            "required": False,
            "description": t("Request timeout in seconds"),
        },
        default=60,
    )


class CustomaiProvider(BaseProvider):
    PROVIDER_DISPLAY_NAME = "Custom AI"
    PROVIDER_CATEGORY = ["AI"]
    PROVIDER_SCOPE = ["connected"]

    def __init__(
        self, context_manager: ContextManager, provider_id: str, config: ProviderConfig
    ):
        super().__init__(context_manager, provider_id, config)
        self._client = None

    def validate_config(self):
        self.authentication_config = CustomaiProviderAuthConfig(
            **self.config.authentication
        )
        # Parse models into a list
        models_str = self.authentication_config.models or "gpt-4o-mini"
        self._models = [m.strip() for m in models_str.split(",") if m.strip()]
        if not self._models:
            self._models = ["gpt-4o-mini"]
        self.authentication_config.models = ",".join(self._models)

    @property
    def client(self) -> OpenAI:
        if self._client is None:
            self._client = OpenAI(
                api_key=self.authentication_config.api_key,
                base_url=self.authentication_config.base_url.rstrip("/"),
                timeout=self.authentication_config.timeout,
            )
        return self._client

    def dispose(self):
        self._client = None

    def validate_scopes(self) -> dict[str, bool | str]:
        try:
            # Try a simple models list request to validate connection
            self.client.models.list()
            return {"connected": True}
        except Exception as e:
            logger.warning(f"Failed to validate CustomAI provider: {e}")
            return {"connected": str(e)}

    def _query(
        self,
        prompt: str,
        model: Optional[str] = None,
        max_tokens: int = 1024,
        system_prompt: Optional[str] = None,
        structured_output_format: Optional[dict] = None,
        **kwargs,
    ):
        """
        Query the AI API with the given prompt.

        Args:
            prompt (str): The user query.
            model (str): The model to use. If not provided, uses the first model in the list.
            max_tokens (int): Maximum tokens to generate.
            system_prompt (str): Optional system prompt.
            structured_output_format (dict): Optional structured output format.
            **kwargs: Additional arguments to pass to the API.
        """
        # Use provided model or first in list
        models_to_try = []
        if model:
            models_to_try = [model]
        else:
            models_to_try = self._models.copy()

        last_error = None

        for attempt_model in models_to_try:
            try:
                messages = []
                if system_prompt:
                    messages.append({"role": "system", "content": system_prompt})
                messages.append({"role": "user", "content": prompt})

                request_kwargs = {
                    "model": attempt_model,
                    "messages": messages,
                    "max_tokens": max_tokens,
                }

                if structured_output_format:
                    request_kwargs["response_format"] = structured_output_format

                # Add any additional kwargs
                for key, value in kwargs.items():
                    if key not in request_kwargs and value is not None:
                        request_kwargs[key] = value

                response = self.client.chat.completions.create(**request_kwargs)
                response_text = response.choices[0].message.content

                # Try to parse as JSON if structured output is expected
                if structured_output_format:
                    try:
                        response_text = json.loads(response_text)
                    except (json.JSONDecodeError, TypeError):
                        pass

                return {
                    "response": response_text,
                    "model_used": attempt_model,
                    "provider": "customai",
                }

            except APIStatusError as e:
                last_error = e
                logger.warning(
                    f"CustomAI provider API error with model {attempt_model}: {e}"
                )
                if e.status_code == 401 or e.status_code == 403:
                    # Auth error - don't try next model
                    break
                # For other errors (rate limit, server error), try next model
                continue
            except Exception as e:
                last_error = e
                logger.warning(f"CustomAI provider error with model {attempt_model}: {e}")
                continue

        # All models failed
        error_msg = f"All models failed. Last error: {last_error}"
        logger.error(error_msg)
        raise Exception(error_msg)

    def _notify(
        self,
        message: str,
        model: Optional[str] = None,
        **kwargs,
    ):
        """
        Send a notification/message using the AI API (same as query but simpler).
        """
        return self._query(prompt=message, model=model, **kwargs)


if __name__ == "__main__":
    import os

    logging.basicConfig(level=logging.DEBUG, handlers=[logging.StreamHandler()])
    context_manager = ContextManager(
        tenant_id="singletenant",
        workflow_id="test",
    )

    api_key = os.environ.get("CUSTOM_AI_API_KEY")
    base_url = os.environ.get("CUSTOM_AI_BASE_URL", "https://api.openai.com/v1")
    models = os.environ.get("CUSTOM_AI_MODELS", "gpt-4o-mini")

    config = ProviderConfig(
        description="Custom AI Provider",
        authentication={
            "api_key": api_key,
            "base_url": base_url,
            "models": models,
        },
    )

    provider = CustomaiProvider(
        context_manager=context_manager,
        provider_id="customai_provider",
        config=config,
    )

    print(
        provider.query(
            prompt="What is the capital of France?",
            system_prompt="You are a helpful assistant.",
        )
    )
