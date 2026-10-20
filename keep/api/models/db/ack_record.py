"""
告警认领记录（P2，借鉴 FlashDuty 认领/升级设计）。

值班通知发出时生成一条待认领记录（含一次性认领 token），IM 里的认领链接
指向 /ack/{token}；认领动作回写 acked_at/acked_by。MTTA = acked_at - created_at
可由此计算（P3 统计界面消费）。
"""

import datetime
import uuid

from sqlalchemy import Column, Integer
from sqlmodel import Field, SQLModel


def _gen_ack_token() -> str:
    return uuid.uuid4().hex


class AckRecord(SQLModel, table=True):
    __tablename__ = "ackrecord"

    id: int = Field(sa_column=Column(Integer, primary_key=True, autoincrement=True))
    tenant_id: str = Field(nullable=False, max_length=256)
    schedule_name: str = Field(nullable=False, max_length=256)
    alert_name: str = Field(default="", nullable=False, max_length=512)
    # 通知对象（发通知时的当前值班人快照）
    notified_member_name: str = Field(default="", nullable=False, max_length=256)
    notified_phone: str = Field(default="", nullable=False, max_length=32)
    notified_email: str = Field(default="", nullable=False, max_length=256)
    # 一次性认领令牌：/ack/{token}，uuid4 不可枚举，本身就是免登录凭证
    ack_token: str = Field(default_factory=_gen_ack_token, nullable=False, max_length=64, unique=True)
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow, nullable=False)
    acked_at: datetime.datetime | None = Field(default=None)
    acked_by: str | None = Field(default=None, max_length=256)
