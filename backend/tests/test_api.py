"""端到端 API 测试：覆盖开局→赔率→预测→赛果结算→积分的完整链路。"""
import datetime as dt
import os
import tempfile

# 必须在导入 app 之前设置数据库地址，指向临时文件
_tmpdir = tempfile.mkdtemp()
os.environ["LOVECUP_DATABASE_URL"] = f"sqlite:///{_tmpdir}/test.db"

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.core.stages import round_of, Stage as CoreStage  # noqa: E402
from app.core.timeutil import match_day_of  # noqa: E402
from app.models import entities as e  # noqa: E402
from app.models.base import init_db, SessionLocal  # noqa: E402
from app.services import settlement as settle  # noqa: E402

init_db()  # TestClient 不走 lifespan，显式建表
client = TestClient(app)


def _game_payload(player1_name: str = "a", player2_name: str = "b") -> dict:
    return {
        "player1_name": player1_name,
        "player2_name": player2_name,
        "player1_pin": "1111",
        "player2_pin": "2222",
        "admin_pin": "9999",
    }


def _future_kickoff_beijing_afternoon(days: int = 1) -> str:
    """构造一个未来比赛日下午的开赛时间（UTC ISO），保证锁定时刻在未来。"""
    beijing = dt.timezone(dt.timedelta(hours=8))
    target = dt.datetime.now(beijing) + dt.timedelta(days=days)
    kickoff = target.replace(hour=20, minute=0, second=0, microsecond=0)  # 北京 20:00
    return kickoff.astimezone(dt.timezone.utc).replace(tzinfo=None).isoformat()


def _create_match(game_id: str, *, stage=e.Stage.GROUP, home="巴西", away="韩国", days=1) -> str:
    kickoff = dt.datetime.fromisoformat(_future_kickoff_beijing_afternoon(days))
    match = e.Match(
        id=f"test_m_{dt.datetime.utcnow().timestamp()}",
        game_id=game_id,
        stage=stage,
        round=e.RoundName(round_of(CoreStage(stage.value)).value),
        home_team=home,
        away_team=away,
        kickoff_at=kickoff,
        match_day=match_day_of(kickoff),
    )
    db = SessionLocal()
    try:
        db.add(match)
        db.commit()
        return match.id
    finally:
        db.close()


def _settle_match(match_id: str, home_goals: int, away_goals: int):
    db = SessionLocal()
    try:
        match = db.get(e.Match, match_id)
        match.home_goals = home_goals
        match.away_goals = away_goals
        scores = settle.settle_match(db, match)
        settle.recompute_standings(db, match.game_id)
        return {
            s.player_id: {"score": s.score, "mode": s.mode, "odds_used": s.odds_used}
            for s in scores
        }
    finally:
        db.close()


def test_full_flow_group_double_underdog():
    # 1. 开局设置
    r = client.post("/api/games", json=_game_payload("wool", "mei"))
    assert r.status_code == 200, r.text
    game = r.json()
    gid = game["id"]
    p1, p2 = game["players"][0]["id"], game["players"][1]["id"]

    # 2. 准备一场小组赛（赛程由系统同步，测试中直接造一场未来比赛）
    mid = _create_match(gid)

    # 3. 录入赔率（客胜冷门 5.00）
    r = client.post(f"/api/matches/{mid}/odds", json={
        "admin_pin": "9999",
        "recorded_by": "wool", "home_odds": "1.30", "draw_odds": "5.00",
        "away_odds": "5.00", "available": True, "source": "OddsPortal",
    })
    assert r.status_code == 200, r.text

    # 4. 两名玩家提交预测：p1 押客胜 0:1 + Double；p2 押主胜仅胜负
    r = client.post(f"/api/matches/{mid}/predictions", json={
        "player_id": p1, "player_pin": "1111", "wdl": "客胜", "has_score": True,
        "pred_home": 0, "pred_away": 1, "use_double": True,
    })
    assert r.status_code == 200, r.text
    assert r.json()["bound_away_odds"] == "5.00"
    r = client.post(f"/api/matches/{mid}/predictions", json={
        "player_id": p2, "player_pin": "2222", "wdl": "主胜",
    })
    assert r.status_code == 200, r.text

    # 5. 预测后修改赔率，结算仍应使用预测提交时绑定的 5.00
    r = client.post(f"/api/matches/{mid}/odds", json={
        "admin_pin": "9999",
        "recorded_by": "wool", "home_odds": "1.30", "draw_odds": "3.00",
        "away_odds": "2.00", "available": True, "source": "OddsPortal",
    })
    assert r.status_code == 200, r.text

    # 6. 自动赛果服务写入 0:1（客胜冷门命中）
    scores = _settle_match(mid, 0, 1)
    from decimal import Decimal
    # p1：Double 押中冷门 = 1×(5.00−1) + 净胜球1 + 精确比分2 = 7（PRD §6 #5）
    assert scores[p1]["score"] == Decimal(7)
    assert scores[p1]["odds_used"] == Decimal("5.00")
    assert scores[p1]["mode"] == e.ScoreMode.DOUBLE
    # p2：押主胜错 → 0
    assert scores[p2]["score"] == Decimal(0)


def test_double_disabled_on_final():
    r = client.post("/api/games", json=_game_payload())
    game = r.json()
    gid = game["id"]
    p1 = game["players"][0]["id"]

    mid = _create_match(gid, stage=e.Stage.FINAL, home="法国", away="阿根廷", days=2)
    client.post(f"/api/matches/{mid}/odds", json={
        "admin_pin": "9999",
        "recorded_by": "a", "home_odds": "2.00", "draw_odds": "3.00", "away_odds": "3.50",
    })
    # 决赛禁用 Double：提交 use_double=True 应被拒
    r = client.post(f"/api/matches/{mid}/predictions", json={
        "player_id": p1, "player_pin": "1111", "wdl": "主胜", "use_double": True,
    })
    assert r.status_code == 422
    assert "决赛禁用" in r.text


def test_prediction_requires_player_pin():
    r = client.post("/api/games", json=_game_payload())
    game = r.json()
    gid = game["id"]
    p1 = game["players"][0]["id"]
    mid = _create_match(gid, days=2)

    r = client.post(f"/api/matches/{mid}/predictions", json={
        "player_id": p1, "player_pin": "wrong", "wdl": "主胜",
    })
    assert r.status_code == 403
    assert "玩家 PIN" in r.text

    r = client.post(f"/api/matches/{mid}/predictions", json={
        "player_id": p1, "player_pin": "1111", "wdl": "主胜",
    })
    assert r.status_code == 200


def test_admin_can_reset_player_pin():
    r = client.post("/api/games", json=_game_payload())
    game = r.json()
    gid = game["id"]
    p1 = game["players"][0]["id"]
    mid = _create_match(gid, days=2)

    r = client.post(f"/api/games/{gid}/pins", json={
        "admin_pin": "bad-pin",
        "player1_pin": "3333",
    })
    assert r.status_code == 403

    r = client.post(f"/api/games/{gid}/pins", json={
        "admin_pin": "9999",
        "player1_pin": "3333",
    })
    assert r.status_code == 200
    assert "a" in r.json()["updated"]

    r = client.post(f"/api/matches/{mid}/predictions", json={
        "player_id": p1, "player_pin": "1111", "wdl": "主胜",
    })
    assert r.status_code == 403

    r = client.post(f"/api/matches/{mid}/predictions", json={
        "player_id": p1, "player_pin": "3333", "wdl": "主胜",
    })
    assert r.status_code == 200


def test_one_double_per_match_day():
    r = client.post("/api/games", json=_game_payload())
    game = r.json()
    gid = game["id"]
    p1 = game["players"][0]["id"]

    # 同一比赛日两场小组赛
    ids = []
    for home, away in [("德国", "日本"), ("西班牙", "摩洛哥")]:
        mid = _create_match(gid, home=home, away=away, days=3)
        ids.append(mid)
        client.post(f"/api/matches/{mid}/odds", json={
            "admin_pin": "9999",
            "recorded_by": "a", "home_odds": "2.00", "draw_odds": "3.00", "away_odds": "3.50",
        })

    # 第一场用 Double：成功
    r = client.post(f"/api/matches/{ids[0]}/predictions", json={
        "player_id": p1, "player_pin": "1111", "wdl": "主胜", "use_double": True,
    })
    assert r.status_code == 200
    # 第二场也想用 Double：应被拒（每个比赛日至多一场）
    r = client.post(f"/api/matches/{ids[1]}/predictions", json={
        "player_id": p1, "player_pin": "1111", "wdl": "主胜", "use_double": True,
    })
    assert r.status_code == 409
    assert "至多一场" in r.text


def test_export_contains_standings():
    r = client.post("/api/games", json=_game_payload())
    gid = r.json()["id"]
    r = client.get(f"/api/games/{gid}/export")
    assert r.status_code == 200
    body = r.json()
    assert "standings" in body and "game" in body and "audit" in body
