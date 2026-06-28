"""从 football-data.org 同步赛程（小组赛 + 淘汰赛）。"""
from __future__ import annotations

import datetime as dt
import logging
import threading
import time
import uuid

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..core.fixtures import group_round_for_teams
from ..core.stages import round_of, Stage as CoreStage
from ..core.timeutil import match_day_of
from ..models import entities as e
from .auto_result import API_BASE, TEAM_NAME_MAP

log = logging.getLogger(__name__)
_last_sync_at = 0.0
_sync_lock = threading.Lock()

API_STAGE_MAP: dict[str, e.Stage] = {
    "GROUP_STAGE": e.Stage.GROUP,
    "LAST_32": e.Stage.R32,
    "LAST_16": e.Stage.R16,
    "QUARTER_FINALS": e.Stage.QF,
    "SEMI_FINALS": e.Stage.SF,
    "THIRD_PLACE": e.Stage.THIRD,
    "FINAL": e.Stage.FINAL,
}


def _cn(name: str) -> str:
    return TEAM_NAME_MAP.get(name, name)


def _parse_utc(s: str) -> dt.datetime:
    return dt.datetime.fromisoformat(s.replace("Z", "+00:00")).replace(tzinfo=None)


def _round_for_match(stage: e.Stage, home_cn: str, away_cn: str) -> e.RoundName:
    if stage == e.Stage.GROUP:
        return group_round_for_teams(home_cn, away_cn)
    return e.RoundName(round_of(CoreStage(stage.value)).value)


def fetch_api_matches() -> list[dict]:
    token = _api_token()
    if not token:
        log.warning("FOOTBALL_DATA_API_TOKEN 未设置，跳过赛程同步")
        return []
    try:
        resp = httpx.get(
            f"{API_BASE}/competitions/WC/matches",
            headers={"X-Auth-Token": token},
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json().get("matches", [])
    except Exception as exc:
        log.error("football-data.org 赛程请求失败: %s", exc)
        return []


def _api_token() -> str:
    from .auto_result import _api_token as auto_result_api_token

    return auto_result_api_token()


def populate_matches(db: Session, game_id: str) -> int:
    """为新对局从 API 拉取所有赛程（跳过待定队伍的淘汰赛）。"""
    api_matches = fetch_api_matches()
    if not api_matches:
        return _populate_fallback(db, game_id)

    count = 0
    for am in api_matches:
        home_en = (am.get("homeTeam") or {}).get("name")
        away_en = (am.get("awayTeam") or {}).get("name")
        if not home_en or not away_en:
            continue

        stage = API_STAGE_MAP.get(am.get("stage", ""))
        if stage is None:
            continue

        home_cn = _cn(home_en)
        away_cn = _cn(away_en)
        ko = _parse_utc(am["utcDate"])

        db.add(e.Match(
            id=f"m_{uuid.uuid4().hex[:10]}",
            game_id=game_id,
            stage=stage,
            round=_round_for_match(stage, home_cn, away_cn),
            home_team=home_cn,
            away_team=away_cn,
            kickoff_at=ko,
            match_day=match_day_of(ko),
        ))
        count += 1
    return count


def sync_matches_for_game(db: Session, game_id: str, api_matches: list[dict]) -> list[str]:
    """同步一个对局的赛程：新增淘汰赛、更新开赛时间。返回变更日志。"""
    existing = list(db.scalars(select(e.Match).where(e.Match.game_id == game_id)))
    existing_keys: dict[tuple[str, str, str], e.Match] = {
        (m.home_team, m.away_team, m.stage.value): m for m in existing
    }

    changes: list[str] = []
    for am in api_matches:
        home_en = (am.get("homeTeam") or {}).get("name")
        away_en = (am.get("awayTeam") or {}).get("name")
        if not home_en or not away_en:
            continue

        stage = API_STAGE_MAP.get(am.get("stage", ""))
        if stage is None:
            continue

        home_cn = _cn(home_en)
        away_cn = _cn(away_en)
        ko = _parse_utc(am["utcDate"])
        key = (home_cn, away_cn, stage.value)

        if key in existing_keys:
            m = existing_keys[key]
            round_name = _round_for_match(stage, home_cn, away_cn)
            if m.round != round_name:
                old = m.round.value
                m.round = round_name
                changes.append(f"更新轮次: {home_cn} vs {away_cn} {old} → {round_name.value}")
            if m.kickoff_at != ko and m.status == e.MatchStatus.PENDING:
                old = m.kickoff_at.isoformat()
                m.kickoff_at = ko
                m.match_day = match_day_of(ko)
                changes.append(f"更新时间: {home_cn} vs {away_cn} {old} → {ko.isoformat()}")
        else:
            db.add(e.Match(
                id=f"m_{uuid.uuid4().hex[:10]}",
                game_id=game_id,
                stage=stage,
                round=_round_for_match(stage, home_cn, away_cn),
                home_team=home_cn,
                away_team=away_cn,
                kickoff_at=ko,
                match_day=match_day_of(ko),
            ))
            changes.append(f"新增: {home_cn} vs {away_cn} ({stage.value})")

    return changes


def sync_all_games() -> dict:
    """同步所有进行中对局的赛程。"""
    from ..models.base import SessionLocal

    api_matches = fetch_api_matches()
    if not api_matches:
        return {"synced": 0, "error": "no API data"}

    db = SessionLocal()
    try:
        games = list(db.scalars(
            select(e.Game).where(e.Game.status == e.GameStatus.ONGOING)
        ))
        total_changes: list[str] = []
        for game in games:
            changes = sync_matches_for_game(db, game.id, api_matches)
            total_changes.extend(changes)
        if total_changes:
            db.commit()
            log.info("赛程同步: %s", total_changes)
        return {"synced": len(games), "changes": total_changes}
    except Exception:
        db.rollback()
        log.exception("赛程同步出错")
        raise
    finally:
        db.close()


def maybe_sync_matches(min_interval_seconds: int = 300) -> dict:
    """按需触发赛程同步，避免后台任务休眠后页面拿到旧赛程。

    Render 免费实例被唤醒后，APScheduler 的 interval job 不会立刻跑；赛程页打开时
    轻量触发一次同步，可以及时补入已确定的淘汰赛对阵。
    """
    global _last_sync_at
    now = time.time()
    if now - _last_sync_at < min_interval_seconds:
        return {"synced": 0, "changes": [], "skipped": "throttled"}
    if not _sync_lock.acquire(blocking=False):
        return {"synced": 0, "changes": [], "skipped": "in_progress"}
    try:
        _last_sync_at = now
        return sync_all_games()
    finally:
        _sync_lock.release()


def _populate_fallback(db: Session, game_id: str) -> int:
    """API 不可用时的备用硬编码小组赛（仅 72 场）。"""
    from ..core.fixtures import GROUP_FIXTURES_UTC
    count = 0
    for group, home, away, mo, d, h, mi in GROUP_FIXTURES_UTC:
        ko = dt.datetime(2026, mo, d, h, mi)
        db.add(e.Match(
            id=f"m_{uuid.uuid4().hex[:10]}",
            game_id=game_id,
            stage=e.Stage.GROUP,
            round=group_round_for_teams(home, away),
            home_team=home,
            away_team=away,
            kickoff_at=ko,
            match_day=match_day_of(ko),
        ))
        count += 1
    return count
