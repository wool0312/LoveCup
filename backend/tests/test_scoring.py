"""PRD §6 验收用例 —— 11 个场景的输入与期望输出。

每个用例都标注了 PRD 表格中的编号，便于对照复核。
"""
from decimal import Decimal

import pytest

from app.core.scoring import (
    MatchResult,
    Prediction,
    WDL,
    match_score,
    score_double,
    score_normal,
)
from app.core.stages import Stage, stage_points

GROUP = stage_points(Stage.GROUP)
QF = stage_points(Stage.QF)
FINAL = stage_points(Stage.FINAL)


def D(x):
    return Decimal(str(x))


# ── 普通模式 ──────────────────────────────────────────────

def test_case1_group_exact_score_all_hit():
    """#1 小组赛·精确比分全中：预测 2:1，实际 2:1 → 4。"""
    pred = Prediction.from_raw(WDL.HOME, has_score=True, pred_home=2, pred_away=1)
    result = MatchResult.from_goals(2, 1)
    assert score_normal(pred, result, GROUP) == D(4)


def test_case2_group_wdl_and_gd():
    """#2 小组赛·仅胜负+净胜球：预测 1:0，实际 2:1 → 2。"""
    # 只登记了净胜球（has_score=False），净胜球 1 命中
    pred = Prediction.from_raw(WDL.HOME, has_gd=True, sgd=1)
    result = MatchResult.from_goals(2, 1)
    assert score_normal(pred, result, GROUP) == D(2)


def test_case3_group_wdl_only():
    """#3 小组赛·仅胜负：预测 3:1，实际 2:1（净胜球错）→ 1。"""
    pred = Prediction.from_raw(WDL.HOME)
    result = MatchResult.from_goals(2, 1)
    assert score_normal(pred, result, GROUP) == D(1)


def test_case4_group_wdl_wrong():
    """#4 小组赛·胜负错：预测 1:1，实际 2:1 → 0。"""
    pred = Prediction.from_raw(WDL.DRAW)
    result = MatchResult.from_goals(2, 1)
    assert score_normal(pred, result, GROUP) == D(0)


# ── Double 模式 ───────────────────────────────────────────

def test_case5_group_double_underdog_hit():
    """#5 小组赛·Double 押中冷门：押客胜 odds=5.00，预测 0:1 实际 0:1
    → 普通 4 / Double 7。"""
    pred = Prediction.from_raw(
        WDL.AWAY, has_score=True, pred_home=0, pred_away=1, use_double=True
    )
    result = MatchResult.from_goals(0, 1)
    assert score_normal(pred, result, GROUP) == D(4)
    assert score_double(pred, result, GROUP, D("5.00")) == D(7)


def test_case6_group_double_wrong():
    """#6 小组赛·Double 押错：押客胜 odds=5.00，实际 1:0 → 普通 0 / Double −1。"""
    pred = Prediction.from_raw(WDL.AWAY, use_double=True)
    result = MatchResult.from_goals(1, 0)
    assert score_normal(pred, result, GROUP) == D(0)
    assert score_double(pred, result, GROUP, D("5.00")) == D(-1)


def test_case7_group_double_low_odds_favorite():
    """#7 小组赛·Double 押低赔热门：押主胜 odds=1.30，仅胜负，实际主胜
    → 普通 1 / Double 0.30。"""
    pred = Prediction.from_raw(WDL.HOME, use_double=True)
    result = MatchResult.from_goals(2, 0)
    assert score_normal(pred, result, GROUP) == D(1)
    assert score_double(pred, result, GROUP, D("1.30")) == D("0.30")


def test_case8_qf_double_hit():
    """#8 8强·Double 押中：本金 8，odds=3.00，仅胜负，命中 → 普通 8 / Double 16。"""
    pred = Prediction.from_raw(WDL.HOME, use_double=True)
    result = MatchResult.from_knockout(1, 0, advanced_home=True)
    assert score_normal(pred, result, QF) == D(8)
    assert score_double(pred, result, QF, D("3.00")) == D(16)


def test_case9_final_double_disabled():
    """#9 决赛·Double 禁用：use_double 视为 false，预测 2:1 实际 2:1
    → 普通 96 / Double 退化为普通 96。"""
    pred = Prediction.from_raw(
        WDL.HOME, has_score=True, pred_home=2, pred_away=1, use_double=True
    )
    result = MatchResult.from_goals(2, 1)
    assert score_normal(pred, result, FINAL) == D(96)
    # 决赛 is_final=True，score_double 内部退化为普通
    assert score_double(pred, result, FINAL, D("3.00")) == D(96)


def test_case10_odds_missing_falls_back_to_normal():
    """#10 赔率缺失：odds.available=false → 只能普通计分。"""
    pred = Prediction.from_raw(WDL.HOME, use_double=True)
    result = MatchResult.from_goals(2, 0)
    # 通过 match_score 走完整分支：赔率不可用时回退普通
    got = match_score(pred, result, GROUP, odds=None, odds_available=False)
    assert got == D(1)


def test_case11_knockout_penalty_shootout():
    """#11 淘汰赛·点球：120 分钟 1:1，点球主胜；预测主胜+比分 1:1
    → 胜负 + 净胜球(0) + 比分全中。"""
    # 用 8 强阶段举例（w=8, gd=8, sc=16）
    pred = Prediction.from_raw(
        WDL.HOME, has_score=True, pred_home=1, pred_away=1
    )
    result = MatchResult.from_knockout(1, 1, advanced_home=True)
    # 胜负(8) + 净胜球0命中(8) + 比分1:1全中(16) = 32
    assert score_normal(pred, result, QF) == D(32)


# ── match_score 综合分支 ──────────────────────────────────

def test_match_score_no_prediction_is_zero():
    """未提交预测 → 0 分（PRD §9）。"""
    result = MatchResult.from_goals(1, 0)
    assert match_score(None, result, GROUP, odds=None, odds_available=False) == D(0)


def test_match_score_double_active_path():
    """Double 生效条件齐备时走 Double 计分。"""
    pred = Prediction.from_raw(WDL.HOME, use_double=True)
    result = MatchResult.from_goals(2, 0)
    got = match_score(pred, result, GROUP, odds=D("1.30"), odds_available=True)
    assert got == D("0.30")
