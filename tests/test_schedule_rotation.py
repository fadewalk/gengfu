"""
值班排班核心逻辑测试：轮换解析、tenant 隔离降级、provider at 参数归一化。
"""

import datetime
from unittest.mock import MagicMock, patch

from keep.api.bl.schedules import compute_current_member, resolve_oncall_for_context
from keep.api.models.db.schedule import Schedule, ScheduleMember


def _schedule(rotation_type="daily", starts_at=None, timezone="Asia/Shanghai"):
    s = MagicMock(spec=Schedule)
    s.name = "支付值班"
    s.timezone = timezone
    s.rotation_type = rotation_type
    # 基准固定在 2026-10-19 00:00（上海时间）
    s.rotation_starts_at = starts_at or datetime.datetime(2026, 10, 19, 0, 0, 0)
    return s


def _members(*names):
    result = []
    for i, n in enumerate(names):
        m = MagicMock(spec=ScheduleMember)
        m.name = n
        m.phone = f"1380000000{i}"
        m.email = f"{n}@g.cn"
        m.position = i
        result.append(m)
    return result


def _resolve_with(schedule, members, now):
    return compute_current_member(schedule, members, now=now)


class TestRotation:
    def test_daily_first_day_returns_first_member(self):
        schedule = _schedule()
        members = _members("张三", "李四", "王五")
        # 基准日当天 → 第 0 位
        member = _resolve_with(schedule, members, datetime.datetime(2026, 10, 19, 10, 0))
        assert member.name == "张三"

    def test_daily_second_day_returns_second_member(self):
        schedule = _schedule()
        members = _members("张三", "李四", "王五")
        member = _resolve_with(schedule, members, datetime.datetime(2026, 10, 20, 10, 0))
        assert member.name == "李四"

    def test_rotation_wraps_around(self):
        schedule = _schedule()
        members = _members("张三", "李四", "王五")
        # 第 3 天回到第 0 位
        member = _resolve_with(schedule, members, datetime.datetime(2026, 10, 22, 10, 0))
        assert member.name == "张三"

    def test_weekly_rotation(self):
        schedule = _schedule(rotation_type="weekly")
        members = _members("张三", "李四")
        # 第 1 周 → 李四
        assert _resolve_with(schedule, members, datetime.datetime(2026, 10, 26, 10, 0)).name == "李四"
        # 第 2 周 → 回到张三
        assert _resolve_with(schedule, members, datetime.datetime(2026, 11, 2, 10, 0)).name == "张三"

    def test_starts_at_in_future_returns_first(self):
        schedule = _schedule(starts_at=datetime.datetime(2026, 12, 1))
        members = _members("张三", "李四")
        assert _resolve_with(schedule, members, datetime.datetime(2026, 10, 19, 10, 0)).name == "张三"

    def test_unknown_rotation_type_returns_none(self):
        schedule = _schedule(rotation_type="monthly")
        members = _members("张三")
        assert _resolve_with(schedule, members, datetime.datetime(2026, 10, 19, 10, 0)) is None

    def test_no_members_returns_none(self):
        schedule = _schedule()
        assert _resolve_with(schedule, [], datetime.datetime(2026, 10, 19, 10, 0)) is None

    def test_schedule_not_found_returns_none(self):
        schedule = None
        members = _members("张三")
        # schedule 为 None 时第一查询返回 None
        assert _resolve_with(schedule, members, datetime.datetime(2026, 10, 19, 10, 0)) is None


class TestResolveForContext:
    def test_context_returns_empty_on_failure(self):
        with patch("keep.api.bl.schedules.resolve_current_member", return_value=None):
            assert resolve_oncall_for_context("keep", "不存在") == {"name": "", "phone": "", "email": ""}

    def test_context_returns_member_fields(self):
        member = MagicMock()
        member.name = "张三"
        member.phone = "13800000000"
        member.email = "z@g.cn"
        with patch("keep.api.bl.schedules.resolve_current_member", return_value=member):
            assert resolve_oncall_for_context("keep", "支付值班") == {
                "name": "张三", "phone": "13800000000", "email": "z@g.cn",
            }


class TestAtNormalization:
    """provider 端 at 参数归一化：工作流 {{ keep.oncall_phone() }} 渲染产物是字符串。"""

    def test_dingtalk_normalizes_comma_string(self):
        from keep.providers.dingtalk_provider.dingtalk_provider import _normalize_at_list
        assert _normalize_at_list("13800138000, 13900139000") == ["13800138000", "13900139000"]
        assert _normalize_at_list(["13800138000"]) == ["13800138000"]
        assert _normalize_at_list(None) == []
        assert _normalize_at_list("") == []

    def test_wecom_normalizes_comma_string(self):
        from keep.providers.wecom_provider.wecom_provider import _normalize_at_list
        assert _normalize_at_list("13800138000,@all") == ["13800138000", "@all"]

    def test_feishu_normalizes_comma_string(self):
        from keep.providers.feishu_provider.feishu_provider import _normalize_at_list
        assert _normalize_at_list("z@g.cn, o@g.cn") == ["z@g.cn", "o@g.cn"]
