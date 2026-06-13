"""时间与比赛日工具（对应 PRD §4.2 / §10）。

口径：全局用北京时间（UTC+8）。存储用 UTC，展示/归属计算转北京时间。
锁定改为「按场锁定」：每场比赛在开赛前 LOCK_LEAD_HOURS 小时截止预测与赔率录入。
比赛日（noon→noon）仍保留，用于界面分组与「每个比赛日至多一次 Double」。
"""
from __future__ import annotations

import datetime as dt
import os

BEIJING = dt.timezone(dt.timedelta(hours=8))
DAY_BOUNDARY_HOUR = 12   # 比赛日分界：北京 12:00 起算（仅用于归属比赛日与「每日一次 Double」）
LOCK_LEAD_HOURS = float(os.getenv("LOVECUP_LOCK_LEAD_HOURS", "1"))  # 每场开赛前多少小时锁定


def _as_utc(t: dt.datetime) -> dt.datetime:
    """把（可能无 tzinfo 的）时间统一为带时区的 UTC。"""
    return t.replace(tzinfo=dt.timezone.utc) if t.tzinfo is None else t.astimezone(dt.timezone.utc)


def to_beijing(utc_time: dt.datetime) -> dt.datetime:
    """把（视为 UTC 的）时间转为北京时间。"""
    return _as_utc(utc_time).astimezone(BEIJING)


def match_day_of(kickoff_utc: dt.datetime) -> dt.date:
    """根据开赛时间（UTC）推算归属比赛日（北京时间日期）。"""
    return to_beijing(kickoff_utc).date()


def lock_time_for_match(kickoff_utc: dt.datetime) -> dt.datetime:
    """该场比赛的锁定时刻 = 开赛时间 − LOCK_LEAD_HOURS（按场锁定）。返回带时区 UTC。"""
    return _as_utc(kickoff_utc) - dt.timedelta(hours=LOCK_LEAD_HOURS)


def now_utc() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def is_match_locked(kickoff_utc: dt.datetime, *, at: dt.datetime = None) -> bool:
    """该场比赛在某时刻是否已过锁定（开赛前 LOCK_LEAD_HOURS 小时）。"""
    at = at or now_utc()
    return _as_utc(at) >= lock_time_for_match(kickoff_utc)
