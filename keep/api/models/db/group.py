"""
Group and UserGroup database models for group-level data isolation.

Groups provide soft isolation within a tenant:
- Resources can be assigned to a group (group_id FK)
- Users can belong to multiple groups (UserGroup many-to-many)
- group_id IS NULL means "tenant-wide" resource (backward compatible)
"""

from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlmodel import Field, Relationship, SQLModel


class Group(SQLModel, table=True):
    """A group within a tenant for soft data isolation."""

    __tablename__ = "tenant_group"

    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    tenant_id: str = Field(foreign_key="tenant.id", index=True)
    name: str = Field(max_length=255)
    description: Optional[str] = None
    created_by: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    members: list["UserGroup"] = Relationship(back_populates="group")


class UserGroup(SQLModel, table=True):
    """Many-to-many mapping between users and groups."""

    __tablename__ = "user_group"

    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    user_email: str = Field(index=True)
    group_id: str = Field(foreign_key="tenant_group.id", index=True)
    role: str = Field(default="member")  # member or admin
    created_at: datetime = Field(default_factory=datetime.utcnow)

    group: Optional[Group] = Relationship(back_populates="members")
