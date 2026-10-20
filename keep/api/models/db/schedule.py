"""
值班排班模型：值班组 + 有序成员 + 轮换规则。

设计（P1 轻量排班，见 docs/zh/oncall-roadmap.md）：
- 一个 Schedule 是一个值班组，成员按 position 轮换
- rotation_type: daily（每日轮换）| weekly（每周轮换）
- rotation_starts_at 是轮换基准时间：当前值班人 =
  members[floor((now - starts_at) / interval) % len(members)]
"""

import datetime

from sqlalchemy import Column, Integer, UniqueConstraint
from sqlmodel import Field, Relationship, SQLModel


class Schedule(SQLModel, table=True):
    __tablename__ = "schedule"
    __table_args__ = (UniqueConstraint("tenant_id", "name", name="uq_schedule_tenant_name"),)

    id: int = Field(sa_column=Column(Integer, primary_key=True, autoincrement=True))
    tenant_id: str = Field(nullable=False, foreign_key="tenant.id")
    name: str = Field(nullable=False, max_length=256)
    timezone: str = Field(default="Asia/Shanghai", nullable=False, max_length=64)
    rotation_type: str = Field(default="daily", nullable=False, max_length=16)
    rotation_starts_at: datetime.datetime = Field(nullable=False)
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow, nullable=False)
    updated_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow, nullable=False)

    members: list["ScheduleMember"] = Relationship(
        back_populates="schedule",
        sa_relationship_kwargs=dict(cascade="all, delete-orphan", order_by="ScheduleMember.position"),
    )


class ScheduleMember(SQLModel, table=True):
    __tablename__ = "schedule_member"

    id: int = Field(sa_column=Column(Integer, primary_key=True, autoincrement=True))
    schedule_id: int = Field(nullable=False, foreign_key="schedule.id")
    schedule: Schedule = Relationship(back_populates="members")
    name: str = Field(nullable=False, max_length=256)
    phone: str | None = Field(default=None, max_length=32)
    email: str | None = Field(default=None, max_length=256)
    position: int = Field(default=0, nullable=False)
