"""
告警认领（Ack）测试：认领页渲染、认领动作幂等、状态查询、oncall_claimed 语义。
"""

import datetime
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from keep.api.models.db.ack_record import AckRecord
from keep.functions import oncall_claimed


def _record(acked=False):
    return AckRecord(
        tenant_id="keep",
        schedule_name="支付值班",
        alert_name="HighCPU",
        notified_member_name="张三",
        notified_phone="13800000000",
        notified_email="z@g.cn",
        ack_token="tok123",
        created_at=datetime.datetime(2026, 10, 19, 10, 0),
        acked_at=datetime.datetime(2026, 10, 19, 10, 5) if acked else None,
    )


class TestAckRecordModel:
    def test_token_auto_generated_and_unique(self):
        a, b = AckRecord(tenant_id="keep", schedule_name="s"), AckRecord(tenant_id="keep", schedule_name="s")
        assert a.ack_token and b.ack_token and a.ack_token != b.ack_token


class TestOncallClaimed:
    def test_claimed_within_window_returns_true(self):
        from keep.api.bl.schedules import has_claim

        now = datetime.datetime.utcnow()
        claimed = MagicMock(acked_at=now - datetime.timedelta(minutes=1))
        unclaimed = MagicMock(acked_at=None)
        fake_session = MagicMock()
        fake_session.exec.return_value.all.return_value = [unclaimed, claimed]

        with patch("keep.api.bl.schedules._get_session", return_value=fake_session):
            assert has_claim("keep", "支付值班", 30) is True

    def test_unclaimed_within_window_returns_false(self):
        from keep.api.bl.schedules import has_claim

        unclaimed = MagicMock(acked_at=None)
        fake_session = MagicMock()
        fake_session.exec.return_value.all.return_value = [unclaimed]

        with patch("keep.api.bl.schedules._get_session", return_value=fake_session):
            assert has_claim("keep", "支付值班", 30) is False

    def test_exception_returns_false_not_raise(self):
        from keep.api.bl.schedules import has_claim

        with patch(
            "keep.api.bl.schedules._get_session",
            side_effect=RuntimeError("db down"),
        ):
            assert has_claim("keep", "支付值班", 30) is False

    def test_functions_wrapper_injects_default_tenant(self):
        """functions 层 oncall_claimed 未提供 tenant 时降级单租户并透传结果。"""
        with patch("keep.api.bl.schedules.has_claim", return_value=True) as mock_has:
            assert oncall_claimed("支付值班", 15) is True
            mock_has.assert_called_once()
            args = mock_has.call_args[0]
            assert args[1] == "支付值班" and args[2] == 15
