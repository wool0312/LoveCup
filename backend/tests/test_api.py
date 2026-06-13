"""端到端 API 测试：覆盖开局→赔率→预测→赛果结算→积分的完整链路。"""
import datetime as dt
import os
import tempfile

import pytest

# 必须在导入 app 之前设置数据库地址，指向临时文件
_tmpdir = tempfile.mkdtemp()
os.environ["LOVECUP_DATABASE_URL"] = f"sqlite:///{_tmpdir}/test.db"

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.models.base import init_db  # noqa: E402

init_db()  # TestClient 不走 lifespan，显式建表
client = TestClient(app)


def _future_kickoff_beijing_afternoon(days: int = 1) -> str:
    """构造一个未来比赛日下午的开赛时间（UTC ISO），保证锁定时刻在未来。"""
    beijing = dt.timezone(dt.timedelta(hours=8))
    target = dt.datetime.now(beijing) + dt.timedelta(days=days)
    kickoff = target.replace(hour=20, minute=0, second=0, microsecond=0)  # 北京 20:00
    return kickoff.astimezone(dt.timezone.utc).replace(tzinfo=None).isoformat()


def test_full_flow_group_double_underdog():
    # 1. 开局设置
    r = client.post("/api/games", json={"player1_name": "wool", "player2_name": "mei"})
    assert r.status_code == 200, r.text
    game = r.json()
    gid = game["id"]
    p1, p2 = game["players"][0]["id"], game["players"][1]["id"]

    # 2. 创建一场小组赛（未来，未锁定）
    r = client.post(f"/api/games/{gid}/matches", json={
        "stage": "小组赛", "home_team": "巴西", "away_team": "韩国",
        "kickoff_at": _future_kickoff_beijing_afternoon(),
    })
    assert r.status_code == 200, r.text
    m = r.json()
    mid = m["id"]
    assert m["locked"] is False

    # 3. 录入赔率（客胜冷门 5.00）
    r = client.post(f"/api/matches/{mid}/odds", json={
        "recorded_by": "wool", "home_odds": "1.30", "draw_odds": "5.00",
        "away_odds": "5.00", "available": True, "source": "OddsPortal",
    })
    assert r.status_code == 200, r.text

    # 4. 两名玩家提交预测：p1 押客胜 0:1 + Double；p2 押主胜仅胜负
    r = client.post(f"/api/matches/{mid}/predictions", json={
        "player_id": p1, "wdl": "客胜", "has_score": True,
        "pred_home": 0, "pred_away": 1, "use_double": True,
    })
    assert r.status_code == 200, r.text
    r = client.post(f"/api/matches/{mid}/predictions", json={
        "player_id": p2, "wdl": "主胜",
    })
    assert r.status_code == 200, r.text

    # 5. 录入赛果 0:1（客胜冷门命中）
    r = client.post(f"/api/matches/{mid}/result", json={
        "home_goals": 0, "away_goals": 1, "actor": "wool",
    })
    assert r.status_code == 200, r.text
    data = r.json()
    from decimal import Decimal
    scores = {s["player_id"]: s for s in data["scores"]}
    # p1：Double 押中冷门 = 1×(5.00−1) + 净胜球1 + 精确比分2 = 7（PRD §6 #5）
    assert Decimal(scores[p1]["score"]) == Decimal(7)
    assert scores[p1]["mode"] == "Double"
    # p2：押主胜错 → 0
    assert Decimal(scores[p2]["score"]) == Decimal(0)


def test_double_disabled_on_final():
    r = client.post("/api/games", json={"player1_name": "a", "player2_name": "b"})
    game = r.json()
    gid = game["id"]
    p1 = game["players"][0]["id"]

    r = client.post(f"/api/games/{gid}/matches", json={
        "stage": "决赛", "home_team": "法国", "away_team": "阿根廷",
        "kickoff_at": _future_kickoff_beijing_afternoon(2),
    })
    mid = r.json()["id"]
    client.post(f"/api/matches/{mid}/odds", json={
        "recorded_by": "a", "home_odds": "2.00", "draw_odds": "3.00", "away_odds": "3.50",
    })
    # 决赛禁用 Double：提交 use_double=True 应被拒
    r = client.post(f"/api/matches/{mid}/predictions", json={
        "player_id": p1, "wdl": "主胜", "use_double": True,
    })
    assert r.status_code == 422
    assert "决赛禁用" in r.text


def test_one_double_per_match_day():
    r = client.post("/api/games", json={"player1_name": "a", "player2_name": "b"})
    game = r.json()
    gid = game["id"]
    p1 = game["players"][0]["id"]
    kickoff = _future_kickoff_beijing_afternoon(3)

    # 同一比赛日两场小组赛
    ids = []
    for home, away in [("德国", "日本"), ("西班牙", "摩洛哥")]:
        r = client.post(f"/api/games/{gid}/matches", json={
            "stage": "小组赛", "home_team": home, "away_team": away, "kickoff_at": kickoff,
        })
        mid = r.json()["id"]
        ids.append(mid)
        client.post(f"/api/matches/{mid}/odds", json={
            "recorded_by": "a", "home_odds": "2.00", "draw_odds": "3.00", "away_odds": "3.50",
        })

    # 第一场用 Double：成功
    r = client.post(f"/api/matches/{ids[0]}/predictions", json={
        "player_id": p1, "wdl": "主胜", "use_double": True,
    })
    assert r.status_code == 200
    # 第二场也想用 Double：应被拒（每个比赛日至多一场）
    r = client.post(f"/api/matches/{ids[1]}/predictions", json={
        "player_id": p1, "wdl": "主胜", "use_double": True,
    })
    assert r.status_code == 409
    assert "至多一场" in r.text


def test_export_contains_standings():
    r = client.post("/api/games", json={"player1_name": "a", "player2_name": "b"})
    gid = r.json()["id"]
    r = client.get(f"/api/games/{gid}/export")
    assert r.status_code == 200
    body = r.json()
    assert "standings" in body and "game" in body and "audit" in body
