"""AI Model Configuration - database models for multi-model management."""
import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field
from sqlalchemy import Column, DateTime, Index, Text, func
from sqlmodel import Field as SQLField, SQLModel


class AIModelConfig(SQLModel, table=True):
    """Stores AI model endpoint configurations per tenant."""

    __tablename__ = "ai_model_config"

    id: str = SQLField(
        default_factory=lambda: str(uuid.uuid4()), primary_key=True, max_length=36
    )
    tenant_id: str = SQLField(max_length=256, index=True)
    name: str = SQLField(max_length=100)
    provider: str = SQLField(default="openai_compatible", max_length=50)
    base_url: str = SQLField(max_length=500)
    api_key_secret: str = SQLField(
        max_length=200,
        description="SecretManager key name that stores the actual API key",
    )
    model_name: str = SQLField(max_length=100)
    fallback_models: Optional[str] = SQLField(
        default=None,
        sa_column=Column(Text),
        description='JSON array of fallback model names, e.g. ["glm-3","gpt-4o-mini"]',
    )
    is_default: bool = SQLField(default=False)
    priority: int = SQLField(default=0)
    enabled: bool = SQLField(default=True)
    extra_config: Optional[str] = SQLField(
        default=None,
        sa_column=Column(Text),
        description='JSON object with extra params like {"temperature": 0.7}',
    )
    created_by: Optional[str] = SQLField(default=None, max_length=256)
    created_at: Optional[datetime] = SQLField(
        sa_column=Column(
            DateTime(timezone=True),
            name="created_at",
            server_default=func.now(),
        )
    )
    updated_at: Optional[datetime] = SQLField(
        sa_column=Column(
            DateTime(timezone=True),
            name="updated_at",
            onupdate=func.now(),
            server_default=func.now(),
        )
    )

    __table_args__ = (
        Index("ix_ai_model_config_tenant_id", "tenant_id"),
        Index("ix_ai_model_config_tenant_name", "tenant_id", "name", unique=True),
    )


# --- DTOs (Pydantic, not SQLModel, for API request/response) ---


class AIModelConfigCreate(BaseModel):
    name: str = Field(..., max_length=100)
    provider: str = Field(default="openai_compatible", max_length=50)
    base_url: str = Field(..., max_length=500)
    api_key: str = Field(..., description="Plaintext API key – stored in SecretManager")
    model_name: str = Field(..., max_length=100)
    fallback_models: list[str] = Field(default_factory=list)
    is_default: bool = False
    priority: int = 0
    enabled: bool = True
    extra_config: dict | None = None


class AIModelConfigUpdate(BaseModel):
    name: str | None = None
    provider: str | None = None
    base_url: str | None = None
    api_key: str | None = Field(
        default=None, description="If provided, update the stored secret"
    )
    model_name: str | None = None
    fallback_models: list[str] | None = None
    is_default: bool | None = None
    priority: int | None = None
    enabled: bool | None = None
    extra_config: dict | None = None


class AIModelConfigRead(BaseModel):
    id: str
    name: str
    provider: str
    base_url: str
    model_name: str
    fallback_models: list[str]
    is_default: bool
    priority: int
    enabled: bool
    extra_config: dict | None
    created_by: str | None
    created_at: datetime | None
    updated_at: datetime | None
    # api_key is NEVER returned – only a masked hint
    api_key_hint: str = ""

    model_config = {"from_attributes": True}
