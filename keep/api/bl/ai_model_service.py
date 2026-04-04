"""AI Model Configuration Service - unified service for multi-model management."""

import json
import logging
import uuid
from typing import Optional

from openai import OpenAI
from sqlmodel import Session, select

from keep.api.core.db import get_session_sync
from keep.api.models.db.ai_model_config import (
    AIModelConfig,
    AIModelConfigCreate,
    AIModelConfigRead,
    AIModelConfigUpdate,
)
from keep.contextmanager.contextmanager import ContextManager
from keep.secretmanager.secretmanagerfactory import SecretManagerFactory

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _secret_name(tenant_id: str, config_id: str) -> str:
    return f"{tenant_id}_ai_model_{config_id}"


def _read_api_key(tenant_id: str, config_id: str) -> str | None:
    """Read the API key for a model config from SecretManager."""
    try:
        context_manager = ContextManager(tenant_id=tenant_id)
        secret_manager = SecretManagerFactory.get_secret_manager(context_manager)
        return secret_manager.read_secret(secret_name=_secret_name(tenant_id, config_id))
    except Exception:
        return None


def _write_api_key(tenant_id: str, config_id: str, api_key: str) -> None:
    """Write the API key for a model config to SecretManager."""
    context_manager = ContextManager(tenant_id=tenant_id)
    secret_manager = SecretManagerFactory.get_secret_manager(context_manager)
    secret_manager.write_secret(
        secret_name=_secret_name(tenant_id, config_id),
        secret_value=api_key,
    )


def _delete_api_key(tenant_id: str, config_id: str) -> None:
    """Delete the API key for a model config from SecretManager."""
    try:
        context_manager = ContextManager(tenant_id=tenant_id)
        secret_manager = SecretManagerFactory.get_secret_manager(context_manager)
        secret_manager.delete_secret(secret_name=_secret_name(tenant_id, config_id))
    except Exception:
        logger.warning(f"Failed to delete secret for config {config_id}")


def _mask_api_key(api_key: str) -> str:
    """Mask API key, showing only first 4 and last 4 chars."""
    if not api_key or len(api_key) < 12:
        return "****"
    return api_key[:4] + "****" + api_key[-4:]


def _config_to_read(config: AIModelConfig) -> AIModelConfigRead:
    """Convert a DB AIModelConfig row to an AIModelConfigRead DTO."""
    api_key_hint = ""
    api_key = _read_api_key(config.tenant_id, config.id)
    if api_key:
        api_key_hint = _mask_api_key(api_key)

    fallback_models = []
    if config.fallback_models:
        try:
            fallback_models = json.loads(config.fallback_models)
        except (json.JSONDecodeError, TypeError):
            fallback_models = []

    extra_config = None
    if config.extra_config:
        try:
            extra_config = json.loads(config.extra_config)
        except (json.JSONDecodeError, TypeError):
            extra_config = None

    return AIModelConfigRead(
        id=config.id,
        name=config.name,
        provider=config.provider,
        base_url=config.base_url,
        model_name=config.model_name,
        fallback_models=fallback_models,
        is_default=config.is_default,
        priority=config.priority,
        enabled=config.enabled,
        extra_config=extra_config,
        created_by=config.created_by,
        created_at=config.created_at,
        updated_at=config.updated_at,
        api_key_hint=api_key_hint,
    )


# ---------------------------------------------------------------------------
# Model Config CRUD
# ---------------------------------------------------------------------------


def list_configs(tenant_id: str) -> list[AIModelConfigRead]:
    """List all AI model configurations for a tenant."""
    with get_session_sync() as session:
        statement = (
            select(AIModelConfig)
            .where(AIModelConfig.tenant_id == tenant_id)
            .order_by(AIModelConfig.created_at.desc())
        )
        configs = session.exec(statement).all()
        return [_config_to_read(c) for c in configs]


def get_config(tenant_id: str, config_id: str) -> AIModelConfigRead | None:
    """Get a single AI model configuration."""
    with get_session_sync() as session:
        config = session.exec(
            select(AIModelConfig).where(
                AIModelConfig.tenant_id == tenant_id,
                AIModelConfig.id == config_id,
            )
        ).first()
        if not config:
            return None
        return _config_to_read(config)


def create_config(
    tenant_id: str, data: AIModelConfigCreate, created_by: str
) -> AIModelConfigRead:
    """Create a new AI model configuration. API key is stored in SecretManager."""
    config_id = str(uuid.uuid4())

    # Store API key in SecretManager
    _write_api_key(tenant_id, config_id, data.api_key)

    with get_session_sync() as session:
        # If this is set as default, clear other defaults
        if data.is_default:
            existing_defaults = session.exec(
                select(AIModelConfig).where(
                    AIModelConfig.tenant_id == tenant_id,
                    AIModelConfig.is_default == True,  # noqa: E712
                )
            ).all()
            for d in existing_defaults:
                d.is_default = False
                session.add(d)

        fallback_json = json.dumps(data.fallback_models) if data.fallback_models else None
        extra_json = json.dumps(data.extra_config) if data.extra_config else None

        config = AIModelConfig(
            id=config_id,
            tenant_id=tenant_id,
            name=data.name,
            provider=data.provider,
            base_url=data.base_url,
            api_key_secret=_secret_name(tenant_id, config_id),
            model_name=data.model_name,
            fallback_models=fallback_json,
            is_default=data.is_default,
            priority=data.priority,
            enabled=data.enabled,
            extra_config=extra_json,
            created_by=created_by,
        )
        session.add(config)
        session.commit()
        session.refresh(config)
        return _config_to_read(config)


def update_config(
    tenant_id: str, config_id: str, data: AIModelConfigUpdate
) -> AIModelConfigRead:
    """Update an existing AI model configuration."""
    with get_session_sync() as session:
        config = session.exec(
            select(AIModelConfig).where(
                AIModelConfig.tenant_id == tenant_id,
                AIModelConfig.id == config_id,
            )
        ).first()
        if not config:
            raise ValueError("AI model configuration not found")

        # If setting as default, clear other defaults
        if data.is_default:
            existing_defaults = session.exec(
                select(AIModelConfig).where(
                    AIModelConfig.tenant_id == tenant_id,
                    AIModelConfig.is_default == True,  # noqa: E712
                    AIModelConfig.id != config_id,
                )
            ).all()
            for d in existing_defaults:
                d.is_default = False
                session.add(d)

        # Update fields
        if data.name is not None:
            config.name = data.name
        if data.provider is not None:
            config.provider = data.provider
        if data.base_url is not None:
            config.base_url = data.base_url
        if data.model_name is not None:
            config.model_name = data.model_name
        if data.fallback_models is not None:
            config.fallback_models = json.dumps(data.fallback_models)
        if data.is_default is not None:
            config.is_default = data.is_default
        if data.priority is not None:
            config.priority = data.priority
        if data.enabled is not None:
            config.enabled = data.enabled
        if data.extra_config is not None:
            config.extra_config = json.dumps(data.extra_config)

        # Update API key if provided
        if data.api_key:
            _write_api_key(tenant_id, config_id, data.api_key)

        session.add(config)
        session.commit()
        session.refresh(config)
        return _config_to_read(config)


def delete_config(tenant_id: str, config_id: str) -> bool:
    """Delete an AI model configuration and its stored secret."""
    # Delete the API key from SecretManager
    _delete_api_key(tenant_id, config_id)

    with get_session_sync() as session:
        config = session.exec(
            select(AIModelConfig).where(
                AIModelConfig.tenant_id == tenant_id,
                AIModelConfig.id == config_id,
            )
        ).first()
        if not config:
            return False

        session.delete(config)
        session.commit()
        return True


# ---------------------------------------------------------------------------
# Client Resolution (with fallback / round-robin)
# ---------------------------------------------------------------------------


def _try_create_client(tenant_id: str, config: AIModelConfig) -> tuple[OpenAI, str] | None:
    """Try to create an OpenAI client from a config. Returns None if API key missing."""
    api_key = _read_api_key(tenant_id, config.id)
    if not api_key:
        return None
    return OpenAI(api_key=api_key, base_url=config.base_url or None), config.model_name


def _resolve_model(tenant_id: str) -> tuple[OpenAI, str]:
    """
    Resolve an OpenAI client and model name.

    Strategy:
    1. Try the default enabled model
    2. If default has fallback_models defined, try them in order
    3. Try other enabled models in priority order (round-robin)
    4. Raise ValueError if nothing works
    """
    with get_session_sync() as session:
        # Get all enabled configs, ordered by priority
        all_configs = session.exec(
            select(AIModelConfig)
            .where(
                AIModelConfig.tenant_id == tenant_id,
                AIModelConfig.enabled == True,  # noqa: E712
            )
            .order_by(AIModelConfig.priority.desc())
        ).all()

        if not all_configs:
            raise ValueError(
                "AI service is not configured: no enabled models found. "
                "Please configure AI models in Settings > AI Configuration."
            )

        # 1. Find the default config
        default_config = next((c for c in all_configs if c.is_default), None)

        if default_config:
            result = _try_create_client(tenant_id, default_config)
            if result:
                return result

            # 2. Try fallback_models if defined
            if default_config.fallback_models:
                try:
                    fallback_names = json.loads(default_config.fallback_models)
                    for fb_model_name in fallback_names:
                        if fb_model_name == default_config.model_name:
                            continue
                        # Re-use same API key/base_url, just swap model name
                        api_key = _read_api_key(tenant_id, default_config.id)
                        if api_key:
                            client = OpenAI(
                                api_key=api_key,
                                base_url=default_config.base_url or None,
                            )
                            return client, fb_model_name
                except (json.JSONDecodeError, TypeError):
                    pass

        # 3. Try other enabled models as fallback (round-robin by priority)
        for config in all_configs:
            if config.id == (default_config.id if default_config else None):
                continue
            result = _try_create_client(tenant_id, config)
            if result:
                return result

    raise ValueError(
        "AI service is not configured: no available model could be resolved. "
        "Please configure AI models in Settings > AI Configuration."
    )


def get_client(tenant_id: str) -> OpenAI:
    """Get an OpenAI client (with fallback chain)."""
    client, _ = _resolve_model(tenant_id)
    return client


def get_model_name(tenant_id: str) -> str:
    """Get the model name (with fallback chain)."""
    _, model_name = _resolve_model(tenant_id)
    return model_name


# ---------------------------------------------------------------------------
# Connection Testing
# ---------------------------------------------------------------------------


def test_connection(tenant_id: str, config_id: str) -> dict:
    """Test the connection to an AI model endpoint."""
    with get_session_sync() as session:
        config = session.exec(
            select(AIModelConfig).where(
                AIModelConfig.tenant_id == tenant_id,
                AIModelConfig.id == config_id,
            )
        ).first()
        if not config:
            return {"success": False, "message": "Configuration not found", "model": ""}

    api_key = _read_api_key(tenant_id, config_id)
    if not api_key:
        return {
            "success": False,
            "message": "API key not found in secret store",
            "model": config.model_name,
        }

    try:
        client = OpenAI(
            api_key=api_key,
            base_url=config.base_url or None,
        )
        client.chat.completions.create(
            model=config.model_name,
            messages=[{"role": "user", "content": "Hello"}],
            max_tokens=5,
        )
        return {
            "success": True,
            "message": "Connection successful",
            "model": config.model_name,
        }
    except Exception as e:
        logger.error(f"Connection test failed for config {config_id}: {e}")
        return {
            "success": False,
            "message": str(e),
            "model": config.model_name,
        }
