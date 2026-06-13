"""定时任务：自动锁定 + 自动结算。"""
from __future__ import annotations

import logging

from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy import select

from .core.timeutil import is_match_locked, now_utc
from .models import entities as e
from .models.base import SessionLocal

log = logging.getLogger(__name__)
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


def _auto_settle() -> None:
    from .services.auto_result import fetch_and_settle
    try:
        result = fetch_and_settle()
        if result.get("settled"):
            log.info("自动结算完成: %s", result["settled"])
    except Exception:
        log.exception("自动结算任务异常")


def _sync_matches() -> None:
    from .services.match_sync import sync_all_games
    try:
        result = sync_all_games()
        if result.get("changes"):
            log.info("赛程同步: %s", result["changes"])
    except Exception:
        log.exception("赛程同步任务异常")


def start_scheduler() -> BackgroundScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = BackgroundScheduler(timezone="UTC")
        _scheduler.add_job(_auto_lock_due_matches, "interval", minutes=1, id="auto_lock")
        _scheduler.add_job(_auto_settle, "interval", minutes=5, id="auto_settle")
        _scheduler.add_job(_sync_matches, "interval", minutes=30, id="sync_matches")
        _scheduler.start()
    return _scheduler
