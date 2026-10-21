"""
告警认领（Ack）API。

设计（借鉴 FlashDuty 认领/升级机制，见 docs/zh/oncall-roadmap.md）：
- 值班通知发出前经 keep.oncall_ack_link() 创建待认领记录，消息里附认领链接
- 认领链接 /ack/{token} 免登录（token 为 uuid4，本身就是凭证），值班人手机点开即认领
- 升级检查：keep.oncall_claimed(schedule, minutes) 供工作流 if 判断超时未认领

MTTA = acked_at - created_at，数据保留在 ackrecord 表（P3 统计消费）。
"""

import datetime
import logging

from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse
from sqlmodel import select
from sqlalchemy.orm import Session

from keep.api.core.db import get_session
from keep.api.models.db.ack_record import AckRecord
from keep.identitymanager.authenticatedentity import AuthenticatedEntity
from keep.identitymanager.identitymanagerfactory import IdentityManagerFactory

logger = logging.getLogger(__name__)

router = APIRouter()

_ACK_PAGE = """<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>更夫 · 告警认领</title>
<style>
  body {{ font-family: -apple-system, "PingFang SC", sans-serif; display: flex;
         align-items: center; justify-content: center; min-height: 100vh;
         background: #181c2e; margin: 0; }}
  .card {{ background: #fff; border-radius: 16px; padding: 32px 40px;
          text-align: center; max-width: 420px; }}
  h1 {{ font-size: 20px; margin: 0 0 8px; }}
  p {{ color: #667; margin: 4px 0; }}
  .alert {{ font-weight: 600; color: #1a1c2e; word-break: break-all; }}
  button {{ margin-top: 20px; background: #ff9a2e; color: #2d2614; border: 0;
           border-radius: 10px; padding: 12px 40px; font-size: 16px;
           font-weight: 600; cursor: pointer; }}
  button:disabled {{ background: #bbb; cursor: default; }}
  .done {{ color: #0a7d38; font-size: 18px; font-weight: 600; }}
</style>
</head>
<body>
<div class="card">
  <h1>更夫 · 值班认领</h1>
  <p>告警：<span class="alert">{alert_name}</span></p>
  <p>值班人：{member_name}</p>
  <p>触发时间：{created_at}</p>
  {body}
</div>
</body>
</html>"""


def _render_page(token: str, alert_name: str, member_name: str, created_at, acked: bool) -> HTMLResponse:
    if acked:
        body = '<p class="done">✓ 已认领，感谢响应</p>'
    else:
        body = (
            f'<form method="post" action="/ack/{token}">'
            f'<button type="submit">认领（由我响应）</button></form>'
        )
    html = _ACK_PAGE.format(
        alert_name=alert_name or "（未命名告警）",
        member_name=member_name or "当前值班人",
        created_at=created_at.strftime("%Y-%m-%d %H:%M") if created_at else "-",
        body=body,
    )
    return HTMLResponse(html)


@router.get("/status", description="Whether the schedule has any claim within the last N minutes")
def ack_status(
    schedule: str,
    minutes: int = 30,
    authenticated_entity: AuthenticatedEntity = Depends(
        IdentityManagerFactory.get_auth_verifier(["read:settings"])
    ),
    session: Session = Depends(get_session),
):
    tenant_id = authenticated_entity.tenant_id
    since = datetime.datetime.utcnow() - datetime.timedelta(minutes=minutes)
    records = session.exec(
        select(AckRecord)
        .where(
            AckRecord.tenant_id == tenant_id,
            AckRecord.schedule_name == schedule,
            AckRecord.created_at >= since,
        )
    ).all()
    claimed = [r for r in records if r.acked_at is not None]
    return {
        "claimed": len(claimed) > 0,
        "total": len(records),
        "claimed_count": len(claimed),
        "first_created_at": min((r.created_at for r in records), default=None),
        "first_acked_at": min((r.acked_at for r in records if r.acked_at), default=None),
    }


@router.get("/stats", description="Claim statistics for a schedule (MTTA etc.)")
def ack_stats(
    schedule: str,
    days: int = 30,
    authenticated_entity: AuthenticatedEntity = Depends(
        IdentityManagerFactory.get_auth_verifier(["read:settings"])
    ),
    session: Session = Depends(get_session),
):
    tenant_id = authenticated_entity.tenant_id
    since = datetime.datetime.utcnow() - datetime.timedelta(days=days)
    records = session.exec(
        select(AckRecord).where(
            AckRecord.tenant_id == tenant_id,
            AckRecord.schedule_name == schedule,
            AckRecord.created_at >= since,
        )
    ).all()
    durations = [
        (r.acked_at - r.created_at).total_seconds()
        for r in records
        if r.acked_at is not None
    ]
    return {
        "schedule": schedule,
        "days": days,
        "total": len(records),
        "claimed": len(durations),
        "claim_rate": round(len(durations) / len(records), 2) if records else None,
        # MTTA：平均认领时长（秒）
        "mtta_seconds": round(sum(durations) / len(durations)) if durations else None,
    }
@router.get("/{token}", description="On-call claim page (token-based, no login)")
def ack_page(token: str, session: Session = Depends(get_session)):
    record = session.exec(
        select(AckRecord).where(AckRecord.ack_token == token)
    ).first()
    if record is None:
        return HTMLResponse(
            _ACK_PAGE.format(alert_name="链接无效", member_name="-",
                             created_at="-", body='<p class="done">认领链接不存在或已失效</p>'),
            status_code=404,
        )
    return _render_page(token, record.alert_name, record.notified_member_name,
                        record.created_at, acked=record.acked_at is not None)


@router.post("/{token}", description="Claim the alert (form submit from the claim page)")
def ack_claim(token: str, session: Session = Depends(get_session)):
    record = session.exec(
        select(AckRecord).where(AckRecord.ack_token == token)
    ).first()
    if record is None:
        return HTMLResponse(
            _ACK_PAGE.format(alert_name="链接无效", member_name="-",
                             created_at="-", body='<p class="done">认领链接不存在或已失效</p>'),
            status_code=404,
        )
    if record.acked_at is None:
        record.acked_at = datetime.datetime.utcnow()
        record.acked_by = record.notified_member_name or None
        session.add(record)
        session.commit()
        logger.info("Ack claimed for schedule=%s alert=%s", record.schedule_name, record.alert_name)
    return _render_page(token, record.alert_name, record.notified_member_name,
                        record.created_at, acked=True)


@router.get("/stats", description="Claim statistics for a schedule (MTTA etc.)")
def ack_stats(
    schedule: str,
    days: int = 30,
    authenticated_entity: AuthenticatedEntity = Depends(
        IdentityManagerFactory.get_auth_verifier(["read:settings"])
    ),
    session: Session = Depends(get_session),
):
    tenant_id = authenticated_entity.tenant_id
    since = datetime.datetime.utcnow() - datetime.timedelta(days=days)
    records = session.exec(
        select(AckRecord).where(
            AckRecord.tenant_id == tenant_id,
            AckRecord.schedule_name == schedule,
            AckRecord.created_at >= since,
        )
    ).all()
    durations = [
        (r.acked_at - r.created_at).total_seconds()
        for r in records
        if r.acked_at is not None
    ]
    return {
        "schedule": schedule,
        "days": days,
        "total": len(records),
        "claimed": len(durations),
        "claim_rate": round(len(durations) / len(records), 2) if records else None,
        # MTTA：平均认领时长（秒）
        "mtta_seconds": round(sum(durations) / len(durations)) if durations else None,
    }
