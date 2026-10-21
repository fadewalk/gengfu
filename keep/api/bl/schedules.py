"""
值班排班解析服务：给定值班组名，按轮换规则解析出当前值班人。

供两处消费：
- keep.functions 里的 keep.oncall_mobiles / keep.oncall_emails / keep.oncall_current
  （工作流 with/if 中的 keep.* 调用）
- keep/api/routes/schedules.py（管理 CRUD）
"""

import datetime
import logging

import pytz
from sqlmodel import select

from keep.api.models.db.schedule import Schedule, ScheduleMember

logger = logging.getLogger(__name__)

_ROTATION_INTERVALS = {
    "daily": datetime.timedelta(days=1),
    "weekly": datetime.timedelta(weeks=1),
}


def _get_session():
    # 延迟导入避免循环依赖（functions 模块加载早于 db 初始化）
    from keep.api.core.db import get_session_sync

    return get_session_sync()


def get_schedules_with_members(tenant_id: str) -> list[tuple[Schedule, list[ScheduleMember]]]:
    session = _get_session()
    try:
        schedules = session.exec(
            select(Schedule).where(Schedule.tenant_id == tenant_id).order_by(Schedule.name)
        ).all()
        result = []
        for schedule in schedules:
            members = session.exec(
                select(ScheduleMember)
                .where(ScheduleMember.schedule_id == schedule.id)
                .order_by(ScheduleMember.position)
            ).all()
            result.append((schedule, list(members)))
        return result
    finally:
        session.close()


def compute_current_member(schedule: Schedule, members: list[ScheduleMember], now: datetime.datetime | None = None) -> ScheduleMember | None:
    """纯轮换算法：给定值班组与有序成员，计算当前值班人。"""
    if schedule is None or not members:
        return None
    interval = _ROTATION_INTERVALS.get(schedule.rotation_type)
    if interval is None:
        logger.warning("Unknown rotation type: %s", schedule.rotation_type)
        return None

    tz = pytz.timezone(schedule.timezone)
    now = now or datetime.datetime.utcnow()
    if now.tzinfo is None:
        now = tz.localize(now)
    else:
        now = now.astimezone(tz)
    starts_at = schedule.rotation_starts_at
    if starts_at.tzinfo is None:
        starts_at = tz.localize(starts_at)
    else:
        starts_at = starts_at.astimezone(tz)

    elapsed = (now - starts_at).total_seconds()
    if elapsed < 0:
        # 基准时间在未来：取首位
        return members[0]
    index = int(elapsed // interval.total_seconds()) % len(members)
    return members[index]


def resolve_current_member(tenant_id: str, schedule_name: str, now: datetime.datetime | None = None) -> ScheduleMember | None:
    """按轮换规则解析指定值班组的当前值班人。

    无该组 / 无成员 / 轮换类型未知时返回 None（调用方降级，不抛异常——值班解析
    失败不应该阻断告警通知）。
    """
    session = None
    try:
        session = _get_session()
        schedule = session.exec(
            select(Schedule).where(Schedule.tenant_id == tenant_id, Schedule.name == schedule_name)
        ).first()
        if schedule is None:
            logger.warning("Schedule not found: %s", schedule_name)
            return None
        members = session.exec(
            select(ScheduleMember)
            .where(ScheduleMember.schedule_id == schedule.id)
            .order_by(ScheduleMember.position)
        ).all()
        return compute_current_member(schedule, list(members), now=now)
    except Exception:
        logger.exception("Failed to resolve on-call for schedule %s", schedule_name)
        return None
    finally:
        if session is not None:
            session.close()


def resolve_oncall_for_context(tenant_id: str, schedule_name: str) -> dict:
    """供 keep.functions 调用的统一入口，返回 dict 便于渲染。"""
    member = resolve_current_member(tenant_id, schedule_name)
    if member is None:
        return {"name": "", "phone": "", "email": ""}
    return {
        "name": member.name or "",
        "phone": member.phone or "",
        "email": member.email or "",
    }


def create_ack_record(tenant_id: str, schedule_name: str, alert_name: str) -> tuple[str, ScheduleMember | None]:
    """创建待认领记录，返回 (认领 token, 通知时的当前值班人)。"""
    from keep.api.models.db.ack_record import AckRecord

    member = resolve_current_member(tenant_id, schedule_name)
    token = __import__("uuid").uuid4().hex
    session = None
    try:
        session = _get_session()
        session.add(
            AckRecord(
                tenant_id=tenant_id,
                schedule_name=schedule_name,
                alert_name=alert_name or "",
                notified_member_name=(member.name if member else ""),
                notified_phone=(member.phone if member else "") or "",
                notified_email=(member.email if member else "") or "",
                ack_token=token,
            )
        )
        session.commit()
    finally:
        if session is not None:
            session.close()
    return token, member


def has_claim(tenant_id: str, schedule_name: str, within_minutes: int) -> bool:
    """最近 N 分钟内该值班组的通知是否已有人认领。失败返回 False。"""
    from keep.api.models.db.ack_record import AckRecord

    since = datetime.datetime.utcnow() - datetime.timedelta(minutes=int(within_minutes))
    session = None
    try:
        session = _get_session()
        records = session.exec(
            select(AckRecord).where(
                AckRecord.tenant_id == tenant_id,
                AckRecord.schedule_name == schedule_name,
                AckRecord.created_at >= since,
            )
        ).all()
        return any(r.acked_at is not None for r in records)
    except Exception:
        logger.exception("Failed to check claim status for schedule %s", schedule_name)
        return False
    finally:
        if session is not None:
            session.close()
