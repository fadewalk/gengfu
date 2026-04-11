from datetime import datetime
from uuid import uuid4

from sqlmodel import Column, Field, Index, SQLModel, TEXT


class ChatMessage(SQLModel, table=True):
    __tablename__ = "chat_message"

    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    tenant_id: str = Field(foreign_key="tenant.id", index=True)
    user_email: str = Field(sa_column=Column(TEXT))
    session_id: str = Field(sa_column=Column(TEXT))
    role: str = Field(sa_column=Column(TEXT))  # "user" | "assistant"
    content: str = Field(sa_column=Column(TEXT))
    created_at: datetime = Field(default_factory=datetime.utcnow)

    __table_args__ = (
        Index("ix_chat_message_session_created", "session_id", "created_at"),
        Index("ix_chat_message_user_email", "user_email"),
    )
