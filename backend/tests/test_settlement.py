"""轮次/最终结算与冠军规则测试（PRD §4.6 / §4.7 / §4.8）。"""
from decimal import Decimal

from app.core.settlement import (
    PlayerStanding,
    decide_outcome,
    final_score,
    round_net,
)
from app.core.stages import Round


def D(x):
    return Decimal(str(x))


def test_round_net_allows_negative():
    assert round_net([D(8), D(-1), D("0.30")]) == D("7.30")


def test_final_score_weighted_sum():
    """最终积分 = Σ 轮次净积分 × 权重（7/15/16/18/20/24%）。"""
    nets = {
        Round.R1: D(10),   # ×0.07 = 0.7
        Round.R2: D(20),   # ×0.15 = 3.0
        Round.R3: D(0),
        Round.R4: D(0),
        Round.R5: D(0),
        Round.R6: D(0),
    }
    assert final_score(nets) == D("3.7")


def test_champion_by_final_score():
    a = PlayerStanding("p1", D("10.5"), D(100), 5)
    b = PlayerStanding("p2", D("8.0"), D(120), 9)
    out = decide_outcome(a, b)
    assert out.champion_ids == ["p1"]
    assert out.is_tie is False


def test_tiebreak_by_unweighted_then_exact_hits():
    # 加权积分相同 → 比未加权净积分
    a = PlayerStanding("p1", D("10.0"), D(120), 3)
    b = PlayerStanding("p2", D("10.0"), D(100), 8)
    assert decide_outcome(a, b).champion_ids == ["p1"]

    # 加权与未加权都相同 → 比精确比分命中次数
    a2 = PlayerStanding("p1", D("10.0"), D(100), 3)
    b2 = PlayerStanding("p2", D("10.0"), D(100), 8)
    assert decide_outcome(a2, b2).champion_ids == ["p2"]


def test_co_champions_when_all_equal():
    a = PlayerStanding("p1", D("10.0"), D(100), 5)
    b = PlayerStanding("p2", D("10.0"), D(100), 5)
    out = decide_outcome(a, b)
    assert out.is_tie is True
    assert sorted(out.champion_ids) == ["p1", "p2"]


def test_blowout_threshold():
    """分差比例 ≥ 25% 且冠军积分 > 0 → 大胜。"""
    # 100 vs 70 → 差 30/100 = 30% ≥ 25% → 大胜
    a = PlayerStanding("p1", D(100), D(100), 5)
    b = PlayerStanding("p2", D(70), D(70), 3)
    out = decide_outcome(a, b)
    assert out.blowout is True
    assert out.margin_ratio == D("0.30")

    # 100 vs 80 → 20% < 25% → 非大胜
    c = PlayerStanding("p1", D(100), D(100), 5)
    d = PlayerStanding("p2", D(80), D(80), 3)
    assert decide_outcome(c, d).blowout is False


def test_no_blowout_when_champion_score_not_positive():
    """冠军积分 ≤ 0 时不认定大胜（避免除零/负分误判）。"""
    a = PlayerStanding("p1", D(0), D(0), 5)
    b = PlayerStanding("p2", D(-10), D(-10), 3)
    out = decide_outcome(a, b)
    assert out.champion_ids == ["p1"]
    assert out.blowout is False
