"""计分核心（对应 PRD §5 伪代码）。

设计要点：
- 纯函数，不依赖数据库或框架 —— 满足 PRD "可复核"：任一场比赛得分可由
  保存的数据独立复算出一致结果。
- 全程 Decimal，绝不用 float。
- WDL 与 净胜球/精确比分 相互独立计算：淘汰赛 WDL 按最终晋级方（含点球），
  净胜球/精确比分按加时结束比分（不含点球），见 PRD §4.5。
"""
from __future__ import annotations

import enum
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

from .stages import StagePoints


class WDL(str, enum.Enum):
    HOME = "主胜"
    DRAW = "平"
    AWAY = "客胜"


@dataclass(frozen=True)
class Prediction:
    """一名玩家对一场比赛的预测（核心层，与数据库解耦）。

    has_score 为真时，调用方须保证 has_gd 也为真、sgd = pred_home - pred_away
    （PRD §5 约定）。使用 from_raw() 构造可自动保证这一点。
    """

    wdl: WDL
    has_gd: bool = False
    sgd: Optional[int] = None
    has_score: bool = False
    pred_home: Optional[int] = None
    pred_away: Optional[int] = None
    use_double: bool = False

    @staticmethod
    def from_raw(
        wdl: WDL,
        *,
        has_gd: bool = False,
        sgd: Optional[int] = None,
        has_score: bool = False,
        pred_home: Optional[int] = None,
        pred_away: Optional[int] = None,
        use_double: bool = False,
    ) -> "Prediction":
        # 精确比分蕴含净胜球（PRD §5 约定）
        if has_score:
            if pred_home is None or pred_away is None:
                raise ValueError("has_score 为真时必须提供 pred_home 与 pred_away")
            has_gd = True
            sgd = pred_home - pred_away
        return Prediction(
            wdl=wdl,
            has_gd=has_gd,
            sgd=sgd,
            has_score=has_score,
            pred_home=pred_home,
            pred_away=pred_away,
            use_double=use_double,
        )


@dataclass(frozen=True)
class MatchResult:
    """一场比赛的判定结果（核心层）。

    wdl    —— 胜平负判定（淘汰赛按最终晋级方，含点球）
    sgd    —— 净胜球 = home - away（按加时结束比分，不含点球）
    home   —— 加时结束主队进球
    away   —— 加时结束客队进球
    """

    wdl: WDL
    sgd: int
    home: int
    away: int

    @staticmethod
    def from_goals(home: int, away: int) -> "MatchResult":
        """小组赛：直接由比分推出 WDL。"""
        if home > away:
            wdl = WDL.HOME
        elif home < away:
            wdl = WDL.AWAY
        else:
            wdl = WDL.DRAW
        return MatchResult(wdl=wdl, sgd=home - away, home=home, away=away)

    @staticmethod
    def from_knockout(home: int, away: int, advanced_home: bool) -> "MatchResult":
        """淘汰赛：WDL 按晋级方（含点球），净胜球/比分按加时结束比分。"""
        wdl = WDL.HOME if advanced_home else WDL.AWAY
        return MatchResult(wdl=wdl, sgd=home - away, home=home, away=away)


def score_normal(pred: Prediction, result: MatchResult, sp: StagePoints) -> Decimal:
    """普通模式计分（PRD §5.1）。"""
    if pred.wdl != result.wdl:
        return Decimal(0)
    s = sp.w
    if pred.has_gd and pred.sgd == result.sgd:
        s += sp.gd
    if pred.has_score and pred.pred_home == result.home and pred.pred_away == result.away:
        s += sp.sc
    return s


def score_double(
    pred: Prediction, result: MatchResult, sp: StagePoints, odds: Decimal
) -> Decimal:
    """Double 模式计分（PRD §5.2）。

    odds —— 玩家所押胜平负结果对应、锁定时形成快照的十进制赔率。
    """
    if sp.is_final:  # 决赛禁用，退化为普通
        return score_normal(pred, result, sp)
    stake = sp.stake
    if pred.wdl != result.wdl:
        return -stake  # 押错，亏本金
    s = stake * (odds - Decimal(1))  # 押中，净赚（本金 ×（赔率−1））
    if pred.has_gd and pred.sgd == result.sgd:
        s += sp.gd  # 净胜球按普通分照加（不乘赔率）
    if pred.has_score and pred.pred_home == result.home and pred.pred_away == result.away:
        s += sp.sc  # 精确比分按普通分照加
    return s


def match_score(
    pred: Optional[Prediction],
    result: MatchResult,
    sp: StagePoints,
    odds: Optional[Decimal],
    odds_available: bool,
) -> Decimal:
    """单场得分（PRD §5.3）。

    pred 为 None 表示该玩家未锁定预测 → 0 分。
    Double 生效条件：use_double 且 赔率可用 且 非决赛。
    """
    if pred is None:
        return Decimal(0)
    if pred.use_double and odds_available and odds is not None and not sp.is_final:
        return score_double(pred, result, sp, odds)
    return score_normal(pred, result, sp)
