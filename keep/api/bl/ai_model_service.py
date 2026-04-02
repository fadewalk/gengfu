"""AI Model Configuration Service - unified service for multi-model management."""

import json
import logging
import os
import uuid
from typing import Optional

from openai import OpenAI
from sqlmodel import Session, select

from keep.api.consts import OPENAI_BASE_URL, OPENAI_MODEL_NAME
from keep.api.core.db import get_session_sync
from keep.api.models.db.ai_model_config import (
    AIModelAssignment,
    AIModelAssignmentRead,
    AIModelAssignmentUpdate,
    AIModelConfig,
    AIModelConfigCreate,
    AIModelConfigRead,
    AIModelConfigUpdate,
    AI_SCENARIOS,
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
    """Delete an AI model configuration, its assignments, and stored secret."""
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

        # Delete associated assignments
        assignments = session.exec(
            select(AIModelAssignment).where(
                AIModelAssignment.model_config_id == config_id
            )
        ).all()
        for a in assignments:
            session.delete(a)

        session.delete(config)
        session.commit()
        return True


# ---------------------------------------------------------------------------
# Scenario Assignments
# ---------------------------------------------------------------------------


def get_assignments(tenant_id: str) -> list[AIModelAssignmentRead]:
    """Get all scenario-to-model assignments for a tenant."""
    with get_session_sync() as session:
        assignments = session.exec(
            select(AIModelAssignment)
            .where(AIModelAssignment.tenant_id == tenant_id)
            .order_by(AIModelAssignment.scenario)
        ).all()

        result = []
        for a in assignments:
            config = session.exec(
                select(AIModelConfig).where(AIModelConfig.id == a.model_config_id)
            ).first()
            result.append(
                AIModelAssignmentRead(
                    id=a.id,
                    scenario=a.scenario,
                    model_config_id=a.model_config_id,
                    model_name=config.model_name if config else "",
                    model_provider=config.provider if config else "",
                    priority=a.priority,
                    enabled=a.enabled,
                )
            )
        return result


def update_assignments(
    tenant_id: str, assignments: list[AIModelAssignmentUpdate]
) -> list[AIModelAssignmentRead]:
    """Update scenario-to-model assignments. Replaces all assignments."""
    with get_session_sync() as session:
        # Delete existing assignments
        existing = session.exec(
            select(AIModelAssignment).where(
                AIModelAssignment.tenant_id == tenant_id
            )
        ).all()
        for e in existing:
            session.delete(e)

        # Create new assignments
        results = []
        for a in assignments:
            if not a.model_config_id:
                continue  # Skip empty assignments
            assignment = AIModelAssignment(
                id=str(uuid.uuid4()),
                tenant_id=tenant_id,
                scenario=a.scenario,
                model_config_id=a.model_config_id,
                priority=a.priority,
                enabled=a.enabled,
            )
            session.add(assignment)

            config = session.exec(
                select(AIModelConfig).where(AIModelConfig.id == a.model_config_id)
            ).first()
            results.append(
                AIModelAssignmentRead(
                    id=assignment.id,
                    scenario=a.scenario,
                    model_config_id=a.model_config_id,
                    model_name=config.model_name if config else "",
                    model_provider=config.provider if config else "",
                    priority=a.priority,
                    enabled=a.enabled,
                )
            )

        session.commit()
        return results


# ---------------------------------------------------------------------------
# Client Resolution (with fallback chain)
# ---------------------------------------------------------------------------


def _resolve_model(tenant_id: str, scenario: str) -> tuple[OpenAI, str]:
    """
    Resolve the OpenAI client and model name for a given scenario.
    Fallback chain: DB assignment → DB default config → env vars → raise.
    """
    with get_session_sync() as session:
        # 1. Try scenario assignment
        assignment = session.exec(
            select(AIModelAssignment)
            .where(
                AIModelAssignment.tenant_id == tenant_id,
                AIModelAssignment.scenario == scenario,
                AIModelAssignment.enabled == True,  # noqa: E712
            )
            .order_by(AIModelAssignment.priority.desc())
        ).first()

        if assignment:
            config = session.exec(
                select(AIModelConfig).where(
                    AIModelConfig.id == assignment.model_config_id,
                    AIModelConfig.enabled == True,  # noqa: E712
                )
            ).first()
            if config:
                api_key = _read_api_key(tenant_id, config.id)
                if api_key:
                    client = OpenAI(
                        api_key=api_key,
                        base_url=config.base_url or None,
                    )
                    return client, config.model_name

        # 2. Try default config
        default_config = session.exec(
            select(AIModelConfig).where(
                AIModelConfig.tenant_id == tenant_id,
                AIModelConfig.is_default == True,  # noqa: E712
                AIModelConfig.enabled == True,  # noqa: E712
            )
        ).first()

        if default_config:
            api_key = _read_api_key(tenant_id, default_config.id)
            if api_key:
                client = OpenAI(
                    api_key=api_key,
                    base_url=default_config.base_url or None,
                )
                return client, default_config.model_name

    # 3. Fallback to environment variables
    env_api_key = os.environ.get("OPENAI_API_KEY")
    if env_api_key:
        client = OpenAI(
            api_key=env_api_key,
            base_url=OPENAI_BASE_URL,
        )
        return client, OPENAI_MODEL_NAME

    raise ValueError(
        f"AI service is not configured: no API key found for scenario '{scenario}'. "
        "Configure AI models in Settings > AI, or set OPENAI_API_KEY environment variable."
    )


def get_client(tenant_id: str, scenario: str) -> OpenAI:
    """Get an OpenAI client for a given scenario (with fallback chain)."""
    client, _ = _resolve_model(tenant_id, scenario)
    return client


def get_model_name(tenant_id: str, scenario: str) -> str:
    """Get the model name for a given scenario (with fallback chain)."""
    _, model_name = _resolve_model(tenant_id, scenario)
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
