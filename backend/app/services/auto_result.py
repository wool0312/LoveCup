"""自动获取比赛结果并结算（对接 football-data.org API）。"""
from __future__ import annotations

import logging
import os
import time

import httpx
from sqlalchemy import select

from ..models import entities as e
from ..models.base import SessionLocal
from . import settlement as settle

log = logging.getLogger(__name__)

API_BASE = "https://api.football-data.org/v4"
API_TOKEN = os.getenv("FOOTBALL_DATA_API_TOKEN", "")
_last_fetch_at = 0.0

# football-data.org 英文队名 → 项目中文队名
TEAM_NAME_MAP: dict[str, str] = {
    "Argentina": "阿根廷",
    "Algeria": "阿尔及利亚",
    "Australia": "澳大利亚",
    "Austria": "奥地利",
    "Belgium": "比利时",
    "Bosnia-Herzegovina": "波黑",
    "Brazil": "巴西",
    "Canada": "加拿大",
    "Cape Verde Islands": "佛得角",
    "Colombia": "哥伦比亚",
    "Congo DR": "刚果（金）",
    "Croatia": "克罗地亚",
    "Curaçao": "库拉索",
    "Czechia": "捷克",
    "Ecuador": "厄瓜多尔",
    "Egypt": "埃及",
    "England": "英格兰",
    "France": "法国",
    "Germany": "德国",
    "Ghana": "加纳",
    "Haiti": "海地",
    "Iran": "伊朗",
    "Iraq": "伊拉克",
    "Ivory Coast": "科特迪瓦",
    "Japan": "日本",
    "Jordan": "约旦",
    "Mexico": "墨西哥",
    "Morocco": "摩洛哥",
    "Netherlands": "荷兰",
    "New Zealand": "新西兰",
    "Norway": "挪威",
    "Panama": "巴拿马",
    "Paraguay": "巴拉圭",
    "Portugal": "葡萄牙",
    "Qatar": "卡塔尔",
    "Saudi Arabia": "沙特阿拉伯",
    "Scotland": "苏格兰",
    "Senegal": "塞内加尔",
    "South Africa": "南非",
    "South Korea": "韩国",
    "Spain": "西班牙",
    "Sweden": "瑞典",
    "Switzerland": "瑞士",
    "Tunisia": "突尼斯",
    "Turkey": "土耳其",
    "United States": "美国",
    "Uruguay": "乌拉圭",
    "Uzbekistan": "乌兹别克斯坦",
}


def _cn(name: str) -> str:
    return TEAM_NAME_MAP.get(name, name)


def _api_token() -> str:
    return os.getenv("FOOTBALL_DATA_API_TOKEN", API_TOKEN)


def _find_matches(db, home_cn: str, away_cn: str) -> list[e.Match]:
    """根据中文主客队名找到所有对局中尚未结算的同一场比赛。"""
    return list(db.scalars(
        select(e.Match).where(
            e.Match.home_team == home_cn,
            e.Match.away_team == away_cn,
            e.Match.status.in_([e.MatchStatus.PENDING, e.MatchStatus.LOCKED]),
        )
    ))


def _score_without_penalties(score: dict) -> tuple[int | None, int | None]:
    """取预测计分用比分：有加时取加时结束比分，否则取常规结束比分。"""
    for key in ("extraTime", "fullTime", "regularTime"):
        period = score.get(key) or {}
        home = period.get("home")
        away = period.get("away")
        if home is not None and away is not None:
            return home, away
    return None, None


def maybe_fetch_and_settle(min_interval_seconds: int = 60) -> dict:
    """按需触发自动结算，避免页面刚打开时等后台定时任务。

    多个前端请求可能连续触发这里，所以用进程内最小间隔做轻量节流。
    """
    global _last_fetch_at
    now = time.time()
    if now - _last_fetch_at < min_interval_seconds:
        return {"checked": 0, "settled": [], "skipped": "throttled"}
    _last_fetch_at = now
    return fetch_and_settle()


def fetch_and_settle() -> dict:
    """从 football-data.org 拉取已完赛比赛，自动录入赛果并结算。

    返回 {"checked": N, "settled": [...]} 摘要。
    """
    token = _api_token()
    if not token:
        log.warning("FOOTBALL_DATA_API_TOKEN 未设置，跳过自动结算")
        return {"checked": 0, "settled": [], "error": "no token"}

    try:
        resp = httpx.get(
            f"{API_BASE}/competitions/WC/matches",
            params={"status": "FINISHED"},
            headers={"X-Auth-Token": token},
            timeout=15,
        )
        resp.raise_for_status()
    except Exception as exc:
        log.error("football-data.org API 请求失败: %s", exc)
        return {"checked": 0, "settled": [], "error": str(exc)}

    data = resp.json()
    api_matches = data.get("matches", [])
    settled_list: list[str] = []

    db = SessionLocal()
    try:
        for am in api_matches:
            home_en = am.get("homeTeam", {}).get("name", "")
            away_en = am.get("awayTeam", {}).get("name", "")
            score = am.get("score", {})
            home_goals, away_goals = _score_without_penalties(score)

            if home_goals is None or away_goals is None:
                continue

            home_cn = _cn(home_en)
            away_cn = _cn(away_en)

            matches = _find_matches(db, home_cn, away_cn)
            if not matches:
                continue

            for m in matches:
                # 录入赛果
                if m.status == e.MatchStatus.PENDING:
                    m.status = e.MatchStatus.LOCKED
                    m.locked_at = m.kickoff_at
                    for p in db.scalars(select(e.Prediction).where(e.Prediction.match_id == m.id)):
                        p.locked_at = m.locked_at

                m.home_goals = home_goals
                m.away_goals = away_goals

                # 晋级方仅用于展示；预测计分只看不含点球的比分。
                if m.stage != e.Stage.GROUP:
                    winner = score.get("winner")
                    if winner == "HOME_TEAM":
                        m.advanced_team = e.WDL.HOME
                    elif winner == "AWAY_TEAM":
                        m.advanced_team = e.WDL.AWAY
                db.flush()

                settle.settle_match(db, m)
                settle.recompute_standings(db, m.game_id)
                settled_list.append(f"{home_cn} {home_goals}:{away_goals} {away_cn} ({m.game_id})")
                log.info("自动结算: %s %d:%d %s (%s)", home_cn, home_goals, away_goals, away_cn, m.game_id)

    except Exception:
        db.rollback()
        log.exception("自动结算过程出错")
        raise
    finally:
        db.close()

    return {"checked": len(api_matches), "settled": settled_list}
