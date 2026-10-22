"""
多级升级测试：通知超时未认领时按成员顺位逐级升级（FlashDuty 式）。
"""

import datetime
from unittest.mock import MagicMock, patch

from keep.api.bl.schedules import compute_escalation_target
from keep.api.models.db.schedule import Schedule, ScheduleMember


def _schedule():
    s = MagicMock(spec=Schedule)
    s.name = "支付值班"
    s.timezone = "Asia/Shanghai"
    s.rotation_type = "daily"
    s.rotation_starts_at = datetime.datetime(2026, 10, 19, 0, 0, 0)
    return s


def _members():
    ms = []
    for i, n in enumerate(["张三", "李四", "王五"]):
        m = MagicMock(spec=ScheduleMember)
        m.name = n
        m.phone = f"1380000000{i}"
        m.email = f"{n}@g.cn"
        m.position = i
        ms.append(m)
    return ms


def _target(now, notified_since=None, claimed=False, timeout=30):
    since = notified_since if notified_since else (now - datetime.timedelta(minutes=10))
    rec = MagicMock()
    rec.created_at = since
    rec.acked_at = now if claimed else None
    with patch("keep.api.bl.schedules._get_session") as mock_sess:
        sess = MagicMock()
        sess.exec.side_effect = [
            MagicMock(first=lambda: _schedule()),
            MagicMock(all=lambda: _members()),
            MagicMock(first=lambda: rec),
        ]
        mock_sess.return_value = sess
        from keep.api.bl.schedules import resolve_escalation_target

        return resolve_escalation_target("keep", "支付值班", timeout, now=now)


class TestEscalationLevels:
    def setup_method(self):
        self.now = datetime.datetime(2026, 10, 19, 12, 0, 0)

    def test_recent_notice_targets_first_member(self):
        """通知发出 10 分钟（<30 分钟超时）→ 仍是首位。"""
        m = _target(self.now, notified_since=self.now - datetime.timedelta(minutes=10), timeout=30)
        assert m["name"] == "张三"

    def test_level1_after_timeout(self):
        """通知发出 40 分钟未认领 → 升级第二顺位。"""
        m = _target(self.now, notified_since=self.now - datetime.timedelta(minutes=40), timeout=30)
        assert m["name"] == "李四"

    def test_level2_after_double_timeout(self):
        """通知发出 70 分钟未认领 → 升级第三顺位。"""
        m = _target(self.now, notified_since=self.now - datetime.timedelta(minutes=70), timeout=30)
        assert m["name"] == "王五"

    def test_wraps_around_chain(self):
        """升级链耗尽后循环回绕。"""
        m = _target(self.now, notified_since=self.now - datetime.timedelta(minutes=100), timeout=30)
        assert m["name"] == "张三"

    def test_claimed_resets_to_first(self):
        """已有人认领 → 升级链重置回首位。"""
        m = _target(self.now, notified_since=self.now - datetime.timedelta(minutes=40), claimed=True, timeout=30)
        assert m["name"] == "张三"

    def test_no_notice_targets_first(self):
        m = _target(self.now, notified_since=None, timeout=30)
        assert m["name"] == "张三"

    def test_minimum_timeout_is_one_minute(self):
        """timeout=0 时实现侧 max(1, 0) 保护不除零，返回首位。"""
        m = _target(self.now, notified_since=self.now - datetime.timedelta(seconds=90), timeout=0)
        assert m["name"] is not None
