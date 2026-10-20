"""
告警认领（Ack）测试：认领页渲染、认领动作幂等、状态查询、oncall_claimed 语义。
"""

import datetime
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from keep.api.models.db.ack_record import AckRecord


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
        from keep.functions import oncall_claimed

        now = datetime.datetime.utcnow()
        claimed = MagicMock(acked_at=now - datetime.timedelta(minutes=1))
        unclaimed = MagicMock(acked_at=None)
        fake_session = MagicMock()
        fake_session.exec.return_value.all.return_value = [unclaimed, claimed]

        def _factory():
            yield fake_session

        with patch("keep.functions._get_ack_session_factory", side_effect=lambda: _factory()):
            assert oncall_claimed("支付值班", within_minutes=30) is True

    def test_unclaimed_within_window_returns_false(self):
        from keep.functions import oncall_claimed

        unclaimed = MagicMock(acked_at=None)
        fake_session = MagicMock()
        fake_session.exec.return_value.all.return_value = [unclaimed]

        def _factory():
            yield fake_session

        with patch("keep.functions._get_ack_session_factory", side_effect=lambda: _factory()):
            assert oncall_claimed("支付值班", within_minutes=30) is False

    def test_exception_returns_false_not_raise(self):
        from keep.functions import oncall_claimed

        def _factory():
            raise RuntimeError("db down")

        with patch("keep.functions._get_ack_session_factory", side_effect=_factory):
            assert oncall_claimed("支付值班") is False
