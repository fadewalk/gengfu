"""
值班排班管理 API（设置页「值班管理」）。

P1 轻量排班：值班组 CRUD + 有序成员列表，轮换规则见 docs/zh/oncall-roadmap.md。
"""

import datetime
from typing import Optional

import pydantic
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from keep.api.core.db import get_session
from keep.api.models.db.schedule import Schedule, ScheduleMember
from keep.identitymanager.authenticatedentity import AuthenticatedEntity
from keep.identitymanager.identitymanagerfactory import IdentityManagerFactory

router = APIRouter()


class MemberIn(pydantic.BaseModel):
    name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    position: int = 0


class ScheduleIn(pydantic.BaseModel):
    name: str
    timezone: str = "Asia/Shanghai"
    rotation_type: str = "daily"
    rotation_starts_at: datetime.datetime
    members: list[MemberIn] = []


@router.get("", description="List all on-call schedules for the tenant")
def list_schedules(
    authenticated_entity: AuthenticatedEntity = Depends(
        IdentityManagerFactory.get_auth_verifier(["read:settings"])
    ),
    session: Session = Depends(get_session),
):
    tenant_id = authenticated_entity.tenant_id
    schedules = (
        session.query(Schedule)
        .filter(Schedule.tenant_id == tenant_id)
        .order_by(Schedule.name)
        .all()
    )
    return {
        "schedules": [
            {
                "id": s.id,
                "name": s.name,
                "timezone": s.timezone,
                "rotation_type": s.rotation_type,
                "rotation_starts_at": s.rotation_starts_at.isoformat(),
                "members": sorted(
                    (
                        {
                            "id": m.id,
                            "name": m.name,
                            "phone": m.phone,
                            "email": m.email,
                            "position": m.position,
                        }
                        for m in s.members
                    ),
                    key=lambda m: m["position"],
                ),
            }
            for s in schedules
        ]
    }


@router.post("", description="Create an on-call schedule")
def create_schedule(
    body: ScheduleIn,
    authenticated_entity: AuthenticatedEntity = Depends(
        IdentityManagerFactory.get_auth_verifier(["write:settings"])
    ),
    session: Session = Depends(get_session),
):
    tenant_id = authenticated_entity.tenant_id
    if body.rotation_type not in ("daily", "weekly"):
        raise HTTPException(status_code=400, detail="rotation_type must be daily or weekly")
    exists = (
        session.query(Schedule)
        .filter(Schedule.tenant_id == tenant_id, Schedule.name == body.name)
        .first()
    )
    if exists:
        raise HTTPException(status_code=409, detail="Schedule with this name already exists")

    schedule = Schedule(
        tenant_id=tenant_id,
        name=body.name,
        timezone=body.timezone,
        rotation_type=body.rotation_type,
        rotation_starts_at=body.rotation_starts_at,
    )
    for i, member in enumerate(sorted(body.members, key=lambda m: m.position)):
        schedule.members.append(
            ScheduleMember(
                name=member.name,
                phone=member.phone,
                email=member.email,
                position=member.position if member.position else i,
            )
        )
    session.add(schedule)
    session.commit()
    return {"id": schedule.id, "name": schedule.name}


@router.delete("/{schedule_id}", description="Delete an on-call schedule")
def delete_schedule(
    schedule_id: int,
    authenticated_entity: AuthenticatedEntity = Depends(
        IdentityManagerFactory.get_auth_verifier(["write:settings"])
    ),
    session: Session = Depends(get_session),
):
    tenant_id = authenticated_entity.tenant_id
    schedule = (
        session.query(Schedule)
        .filter(Schedule.tenant_id == tenant_id, Schedule.id == schedule_id)
        .first()
    )
    if schedule is None:
        raise HTTPException(status_code=404, detail="Schedule not found")
    session.delete(schedule)
    session.commit()
    return {"deleted": schedule_id}


@router.put("/{schedule_id}", description="Update an on-call schedule (full replace)")
def update_schedule(
    schedule_id: int,
    body: ScheduleIn,
    authenticated_entity: AuthenticatedEntity = Depends(
        IdentityManagerFactory.get_auth_verifier(["write:settings"])
    ),
    session: Session = Depends(get_session),
):
    tenant_id = authenticated_entity.tenant_id
    schedule = (
        session.query(Schedule)
        .filter(Schedule.tenant_id == tenant_id, Schedule.id == schedule_id)
        .first()
    )
    if schedule is None:
        raise HTTPException(status_code=404, detail="Schedule not found")
    if body.rotation_type not in ("daily", "weekly"):
        raise HTTPException(status_code=400, detail="rotation_type must be daily or weekly")

    schedule.timezone = body.timezone
    schedule.rotation_type = body.rotation_type
    schedule.rotation_starts_at = body.rotation_starts_at
    schedule.updated_at = datetime.datetime.utcnow()

    # 成员全量替换（表单整体保存语义）
    session.query(ScheduleMember).filter(ScheduleMember.schedule_id == schedule.id).delete()
    for i, member in enumerate(sorted(body.members, key=lambda m: m.position)):
        session.add(
            ScheduleMember(
                schedule_id=schedule.id,
                name=member.name,
                phone=member.phone,
                email=member.email,
                position=member.position if member.position else i,
            )
        )
    session.commit()
    return {"id": schedule.id, "name": schedule.name}
