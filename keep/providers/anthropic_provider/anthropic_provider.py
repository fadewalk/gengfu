import json
import dataclasses
import pydantic
from anthropic import Anthropic, AuthenticationError

from keep.api.i18n import t
from keep.contextmanager.contextmanager import ContextManager
from keep.providers.base.base_provider import BaseProvider
from keep.providers.models.provider_config import ProviderConfig


@pydantic.dataclasses.dataclass
class AnthropicProviderAuthConfig:
    api_key: str = dataclasses.field(
        metadata={
            "required": True,
            "description": t("Anthropic API Key"),
            "sensitive": True,
            "hint": "sk-ant-...",
        },
    )

    model: str = dataclasses.field(
        default="claude-sonnet-4-6",
        metadata={
            "required": False,
            "description": t(
                "Model name, e.g. claude-sonnet-4-6, or glm-5.3-flash / kimi-k2 on Anthropic-compatible endpoints"
            ),
            "hint": "claude-sonnet-4-6",
        },
    )

    base_url: str = dataclasses.field(
        default="",
        metadata={
            "required": False,
            "description": t(
                "Custom base_url for Anthropic-compatible endpoints (e.g. https://open.bigmodel.cn/api/anthropic for GLM coding-plan keys)"
            ),
            "hint": "https://open.bigmodel.cn/api/anthropic",
        },
    )

    system_prompt: str = dataclasses.field(
        default="You are an expert SRE and security analyst. Analyze alerts and provide concise, actionable insights.",
        metadata={
            "required": False,
            "description": "System prompt that sets Claude's role for all requests in this provider.",
        },
    )


class AnthropicProvider(BaseProvider):
    PROVIDER_DISPLAY_NAME = "Anthropic"
    PROVIDER_CATEGORY = ["AI"]

    def __init__(
        self, context_manager: ContextManager, provider_id: str, config: ProviderConfig
    ):
        super().__init__(context_manager, provider_id, config)

    def validate_config(self):
        self.authentication_config = AnthropicProviderAuthConfig(
            **self.config.authentication
        )

    def dispose(self):
        pass

    def _build_client(self) -> Anthropic:
        client_kwargs = {"api_key": self.authentication_config.api_key}
        if self.authentication_config.base_url:
            client_kwargs["base_url"] = self.authentication_config.base_url
        return Anthropic(**client_kwargs)

    def validate_scopes(self) -> dict[str, bool | str]:
        try:
            client = self._build_client()
            client.messages.create(
                model=self.authentication_config.model,
                max_tokens=10,
                messages=[{"role": "user", "content": "ping"}],
            )
            return {"api_key_valid": True}
        except AuthenticationError:
            return {"api_key_valid": "Invalid API key — check your Anthropic console."}
        except Exception as e:
            return {"api_key_valid": str(e)}

    def _query(
        self,
        prompt,
        model=None,
        max_tokens=1024,
        system_prompt=None,
        structured_output_format=None,
    ):
        """
        Query the Anthropic API with the given prompt and model.
        Args:
            prompt (str): The prompt to query the model with.
            model (str): The model to query (overrides provider config).
            max_tokens (int): The maximum number of tokens to generate.
            system_prompt (str): System prompt override for this call.
            structured_output_format (dict): The structured output format to use.
        """
        client = self._build_client()

        messages = [{"role": "user", "content": prompt}]

        # Resolve system prompt: call-level override > structured output schema > provider config
        resolved_system = system_prompt or self.authentication_config.system_prompt
        if structured_output_format:
            schema = structured_output_format.get("json_schema", {})
            resolved_system = (
                f"You must respond with valid JSON that matches this schema: {json.dumps(schema)}\n"
                "Your response must be parseable JSON and nothing else."
            )

        response = client.messages.create(
            model=model or self.authentication_config.model,
            max_tokens=max_tokens,
            messages=messages,
            system=resolved_system,
        )

        # 推理模型（如 GLM-5.x / Claude thinking）首个 content 块是 thinking，
        # 只有 text 块带 .text——直接取 content[0] 会 AttributeError
        content = next(
            (block.text for block in response.content if getattr(block, "type", None) == "text"),
            None,
        )
        if content is None:
            raise ValueError(
                f"No text block in Anthropic response (blocks: {[getattr(b, 'type', '?') for b in response.content]})"
            )

        try:
            content = json.loads(content)
        except Exception:
            pass

        return {
            "response": content,
        }


if __name__ == "__main__":
    import os
    import logging

    logging.basicConfig(level=logging.DEBUG, handlers=[logging.StreamHandler()])
    context_manager = ContextManager(
        tenant_id="singletenant",
        workflow_id="test",
    )

    api_key = os.environ.get("ANTHROPIC_API_KEY")

    config = ProviderConfig(
        description="Claude Provider",
        authentication={
            "api_key": api_key,
        },
    )

    provider = AnthropicProvider(
        context_manager=context_manager,
        provider_id="claude_provider",
        config=config,
    )

    print(
        provider.query(
            prompt="Here is an alert, define environment for it: Clients are panicking, nothing works.",
            structured_output_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "environment_restoration",
                    "schema": {
                        "type": "object",
                        "properties": {
                            "environment": {
                                "type": "string",
                                "enum": ["production", "debug", "pre-prod"],
                            },
                        },
                        "required": ["environment"],
                        "additionalProperties": False,
                    },
                    "strict": True,
                },
            },
            max_tokens=100,
        )
    )
