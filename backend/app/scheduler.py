"""自动锁定兜底任务（PRD §8.2）。

每分钟扫描一次：把已过锁定时刻（开赛前 LOCK_LEAD_HOURS 小时）、但仍为「待预测」的比赛
推进到「已锁定」，并给当时的预测打上 locked_at 快照。即使没人手动点锁定，状态也会自动推进。
"""
from __future__ import annotations

from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy import select

from .core.timeutil import is_match_locked, now_utc
from .models import entities as e
from .models.base import SessionLocal

_scheduler: BackgroundScheduler | None = None


def _auto_lock_due_matches() -> None:
    db = SessionLocal()
    try:
        pending = db.scalars(
            select(e.Match).where(e.Match.status == e.MatchStatus.PENDING)
        )
        changed = False
        for m in pending:
            if is_match_locked(m.kickoff_at):
                m.status = e.MatchStatus.LOCKED
                m.locked_at = now_utc().replace(tzinfo=None)
                for p in db.scalars(
                    select(e.Prediction).where(e.Prediction.match_id == m.id)
                ):
                    p.locked_at = m.locked_at
                changed = True
        if changed:
            db.commit()
    finally:
        db.close()


def start_scheduler() -> BackgroundScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = BackgroundScheduler(timezone="UTC")
        _scheduler.add_job(_auto_lock_due_matches, "interval", minutes=1, id="auto_lock")
        _scheduler.start()
    return _scheduler
