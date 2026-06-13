"""自动获取比赛结果并结算（对接 football-data.org API）。"""
from __future__ import annotations

import logging
import os
from typing import Optional

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import entities as e
from ..models.base import SessionLocal
from . import settlement as settle

log = logging.getLogger(__name__)

API_BASE = "https://api.football-data.org/v4"
API_TOKEN = os.getenv("FOOTBALL_DATA_API_TOKEN", "")

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


def _find_match(db: Session, home_cn: str, away_cn: str) -> Optional[e.Match]:
    """根据中文主客队名找到未结算的比赛。"""
    return db.scalar(
        select(e.Match).where(
            e.Match.home_team == home_cn,
            e.Match.away_team == away_cn,
            e.Match.status.in_([e.MatchStatus.PENDING, e.MatchStatus.LOCKED]),
        )
    )


def fetch_and_settle() -> dict:
    """从 football-data.org 拉取已完赛比赛，自动录入赛果并结算。

    返回 {"checked": N, "settled": [...]} 摘要。
    """
    if not API_TOKEN:
        log.warning("FOOTBALL_DATA_API_TOKEN 未设置，跳过自动结算")
        return {"checked": 0, "settled": [], "error": "no token"}

    try:
        resp = httpx.get(
            f"{API_BASE}/competitions/WC/matches",
            params={"status": "FINISHED"},
            headers={"X-Auth-Token": API_TOKEN},
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
            ft = score.get("fullTime", {})
            home_goals = ft.get("home")
            away_goals = ft.get("away")

            if home_goals is None or away_goals is None:
                continue

            home_cn = _cn(home_en)
            away_cn = _cn(away_en)

            m = _find_match(db, home_cn, away_cn)
            if m is None:
                continue

            # 录入赛果
            if m.status == e.MatchStatus.PENDING:
                m.status = e.MatchStatus.LOCKED
                m.locked_at = m.kickoff_at
                for p in db.scalars(select(e.Prediction).where(e.Prediction.match_id == m.id)):
                    p.locked_at = m.locked_at

            m.home_goals = home_goals
            m.away_goals = away_goals

            # 小组赛不需要 advanced_team；淘汰赛需要额外处理
            if m.stage != e.Stage.GROUP:
                winner = score.get("winner")
                if winner == "HOME_TEAM":
                    m.advanced_team = e.WDL.HOME
                elif winner == "AWAY_TEAM":
                    m.advanced_team = e.WDL.AWAY
            db.flush()

            settle.settle_match(db, m)
            settle.recompute_standings(db, m.game_id)
            settled_list.append(f"{home_cn} {home_goals}:{away_goals} {away_cn}")
            log.info("自动结算: %s %d:%d %s", home_cn, home_goals, away_goals, away_cn)

    except Exception:
        db.rollback()
        log.exception("自动结算过程出错")
        raise
    finally:
        db.close()

    return {"checked": len(api_matches), "settled": settled_list}
