"""开发用种子数据：建一个对局 + 几场未来比赛（含赔率），方便前端联调。

用法：cd backend && .venv/bin/python -m scripts.seed
"""
from __future__ import annotations

import datetime as dt
from decimal import Decimal

from app.core.stages import round_of
from app.core.stages import Stage as CoreStage
from app.core.timeutil import match_day_of
from app.models import entities as e
from app.models.base import SessionLocal, init_db

BEIJING = dt.timezone(dt.timedelta(hours=8))


def _kickoff(days: int, hour: int = 20) -> dt.datetime:
    t = (dt.datetime.now(BEIJING) + dt.timedelta(days=days)).replace(
        hour=hour, minute=0, second=0, microsecond=0
    )
    return t.astimezone(dt.timezone.utc).replace(tzinfo=None)


def main() -> None:
    init_db()
    db = SessionLocal()
    try:
        g = e.Game(
            id="g_demo", player1_id="p_wool", player2_id="p_mei",
            player1_name="wool", player2_name="mei",
            japan_budget_cny=Decimal("1000"), rule_version="v0.5",
        )
        db.merge(g)
        db.commit()

        seed_matches = [
            (e.Stage.GROUP, "巴西", "韩国", 1, "1.30", "5.00", "5.00"),
            (e.Stage.GROUP, "德国", "日本", 1, "2.10", "3.30", "3.40"),
            (e.Stage.QF, "法国", "英格兰", 2, "2.00", "3.20", "3.80"),
        ]
        for i, (stage, home, away, days, ho, dr, ao) in enumerate(seed_matches):
            ko = _kickoff(days)
            m = e.Match(
                id=f"m_demo_{i}", game_id="g_demo", stage=stage,
                round=e.RoundName(round_of(CoreStage(stage.value)).value),
                home_team=home, away_team=away, kickoff_at=ko, match_day=match_day_of(ko),
            )
            db.merge(m)
            db.merge(e.OddsSnapshot(
                match_id=f"m_demo_{i}", home_odds=Decimal(ho), draw_odds=Decimal(dr),
                away_odds=Decimal(ao), available=True, recorded_by="wool", source="OddsPortal",
            ))
        db.commit()
        print("种子数据已写入：对局 g_demo，3 场比赛（含赔率）。玩家 p_wool / p_mei")
    finally:
        db.close()


if __name__ == "__main__":
    main()
