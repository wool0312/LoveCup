"""载入 2026 世界杯真实小组赛赛程（来源：联网查询，需人工核对）。

- 保留对局 g_demo 及玩家 wool / mei。
- 先清空该对局下的旧比赛及其衍生数据（赔率/预测/得分/汇总/最终结果），再写入下列场次。
- 开赛时间以 UTC 存储；比赛日与北京时间 12:00 锁定时刻由 timeutil 自动推算。
- 赔率留空：玩家可在「赔率」页自行录入；缺赔率时按规则禁用 Double。

用法：cd backend && .venv/bin/python -m scripts.load_fixtures

⚠️ 赛程与开赛时间来自网络搜索，可能有偏差，请与官方赛程核对后再正式使用。
"""
from __future__ import annotations

import datetime as dt

from sqlalchemy import delete, select

from app.core.stages import round_of
from app.core.stages import Stage as CoreStage
from app.core.timeutil import match_day_of
from app.models import entities as e
from app.models.base import SessionLocal, init_db

GAME_ID = "g_demo"

# (主队, 客队, UTC 年, 月, 日, 时, 分)；均为小组赛。
# 时间换算：北京时间 = UTC + 8 小时。
FIXTURES_UTC: list[tuple[str, str, int, int, int, int, int]] = [
    # —— 比赛日 6/14（北京 6/15 凌晨开球）——
    ("德国", "库拉索", 2026, 6, 14, 17, 0),
    ("荷兰", "日本", 2026, 6, 14, 20, 0),
    ("科特迪瓦", "厄瓜多尔", 2026, 6, 14, 23, 0),
    ("瑞典", "突尼斯", 2026, 6, 15, 2, 0),
    # —— 比赛日 6/15 ——
    ("西班牙", "佛得角", 2026, 6, 15, 16, 0),
    ("比利时", "埃及", 2026, 6, 15, 19, 0),
    ("沙特阿拉伯", "乌拉圭", 2026, 6, 15, 22, 0),
    ("伊朗", "新西兰", 2026, 6, 16, 1, 0),
    # —— 比赛日 6/16 ——
    ("法国", "塞内加尔", 2026, 6, 16, 19, 0),
    ("伊拉克", "挪威", 2026, 6, 16, 22, 0),
    ("阿根廷", "阿尔及利亚", 2026, 6, 17, 1, 0),
    ("奥地利", "约旦", 2026, 6, 17, 4, 0),
    # —— 比赛日 6/17 ——
    ("葡萄牙", "刚果（金）", 2026, 6, 17, 17, 0),
    ("英格兰", "克罗地亚", 2026, 6, 17, 20, 0),
    ("加纳", "巴拿马", 2026, 6, 17, 23, 0),
    ("乌兹别克斯坦", "哥伦比亚", 2026, 6, 18, 2, 0),
    # —— 比赛日 6/18 ——
    ("捷克", "南非", 2026, 6, 18, 16, 0),
    ("瑞士", "波黑", 2026, 6, 18, 19, 0),
    ("加拿大", "卡塔尔", 2026, 6, 18, 22, 0),
    ("墨西哥", "韩国", 2026, 6, 19, 1, 0),
    # —— 比赛日 6/19 ——
    ("美国", "澳大利亚", 2026, 6, 19, 19, 0),
    ("苏格兰", "摩洛哥", 2026, 6, 19, 22, 0),
    ("巴西", "海地", 2026, 6, 20, 0, 30),
    ("土耳其", "巴拉圭", 2026, 6, 20, 3, 0),
    # —— 比赛日 6/20 ——
    ("荷兰", "瑞典", 2026, 6, 20, 17, 0),
    ("德国", "科特迪瓦", 2026, 6, 20, 20, 0),
    ("厄瓜多尔", "库拉索", 2026, 6, 21, 3, 0),
    ("突尼斯", "日本", 2026, 6, 21, 4, 0),
]


def _clear_game_matches(db) -> int:
    """删除该对局下的全部比赛及衍生数据，返回清理的比赛数。"""
    match_ids = db.scalars(
        select(e.Match.id).where(e.Match.game_id == GAME_ID)
    ).all()
    if match_ids:
        db.execute(delete(e.MatchScore).where(e.MatchScore.match_id.in_(match_ids)))
        db.execute(delete(e.Prediction).where(e.Prediction.match_id.in_(match_ids)))
        db.execute(delete(e.OddsSnapshot).where(e.OddsSnapshot.match_id.in_(match_ids)))
        db.execute(delete(e.Match).where(e.Match.id.in_(match_ids)))
    db.execute(delete(e.RoundSummary).where(e.RoundSummary.game_id == GAME_ID))
    db.execute(delete(e.FinalResult).where(e.FinalResult.game_id == GAME_ID))
    return len(match_ids)


def main() -> None:
    init_db()
    db = SessionLocal()
    try:
        db.merge(e.Game(
            id=GAME_ID, player1_id="p_wool", player2_id="p_mei",
            player1_name="wool", player2_name="mei", rule_version="v0.5",
        ))
        removed = _clear_game_matches(db)

        for i, (home, away, y, mo, d, h, mi) in enumerate(FIXTURES_UTC):
            ko = dt.datetime(y, mo, d, h, mi)  # UTC（无 tzinfo），与现有存储口径一致
            db.add(e.Match(
                id=f"m_wc_{i:02d}", game_id=GAME_ID, stage=e.Stage.GROUP,
                round=e.RoundName(round_of(CoreStage(e.Stage.GROUP.value)).value),
                home_team=home, away_team=away,
                kickoff_at=ko, match_day=match_day_of(ko),
            ))
        db.commit()
        print(f"已清理旧比赛 {removed} 场；写入小组赛 {len(FIXTURES_UTC)} 场（对局 {GAME_ID}，玩家 wool/mei）。")
        print("赔率留空，玩家可在「赔率」页自行录入。")
    finally:
        db.close()


if __name__ == "__main__":
    main()
