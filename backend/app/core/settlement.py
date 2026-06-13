"""轮次与最终结算（对应 PRD §4.6 / §4.7 / §4.8 / §5.4）。

纯函数：给定各场得分，汇总出轮次净积分、最终加权积分、冠军与大胜判定。
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from typing import Dict, List, Optional

from .stages import Round, weight_of

TWO_PLACES = Decimal("0.01")


def round_net(match_scores: List[Decimal]) -> Decimal:
    """某轮净积分 = 该轮全部比赛得分之和，可为负（PRD §5.4）。"""
    total = Decimal(0)
    for s in match_scores:
        total += s
    return total


def final_score(round_nets: Dict[Round, Decimal]) -> Decimal:
    """最终积分 = Σ（每轮净积分 × 该轮权重）（PRD §5.4）。

    用未舍入值，排名比较以此为准。
    """
    total = Decimal(0)
    for rnd, net in round_nets.items():
        total += net * weight_of(rnd)
    return total


def display_round(value: Decimal) -> Decimal:
    """展示用：四舍五入保留 2 位小数（PRD §10）。"""
    return value.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class PlayerStanding:
    """用于排名比较的一名玩家汇总（全部为未舍入值）。"""

    player_id: str
    final_score: Decimal           # 最终加权积分
    unweighted_net: Decimal        # 未加权累计净积分（同分次级比较）
    exact_hits: int                # 精确比分命中次数（再次级比较）


@dataclass(frozen=True)
class FinalOutcome:
    champion_ids: List[str]        # 1 人为唯一冠军；2 人为并列冠军
    is_tie: bool
    blowout: bool                  # 大胜（仅唯一冠军且分差比例 ≥ 25% 且冠军积分 > 0）
    margin_ratio: Optional[Decimal]  # 分差比例（未舍入）；并列或无法计算时为 None


def decide_outcome(a: PlayerStanding, b: PlayerStanding) -> FinalOutcome:
    """冠军与同分规则（PRD §4.7）＋ 大胜认定（PRD §4.8(2)）。

    比较顺序：最终加权积分 → 未加权累计净积分 → 精确比分命中次数 → 并列冠军。
    """
    winner, loser = _compare(a, b)

    if winner is None:  # 三级比较仍相同 → 并列冠军
        return FinalOutcome(
            champion_ids=sorted([a.player_id, b.player_id]),
            is_tie=True,
            blowout=False,
            margin_ratio=None,
        )

    blowout = False
    margin_ratio: Optional[Decimal] = None
    # 大胜：分差比例 =（冠军 − 失败者）/ 冠军 ×100%，≥25% 且 冠军积分 > 0
    if winner.final_score > 0:
        margin_ratio = (winner.final_score - loser.final_score) / winner.final_score
        if margin_ratio >= Decimal("0.25"):
            blowout = True

    return FinalOutcome(
        champion_ids=[winner.player_id],
        is_tie=False,
        blowout=blowout,
        margin_ratio=margin_ratio,
    )


def _compare(a: PlayerStanding, b: PlayerStanding):
    """返回 (winner, loser)；三级比较仍相同则返回 (None, None)。"""
    if a.final_score != b.final_score:
        return (a, b) if a.final_score > b.final_score else (b, a)
    if a.unweighted_net != b.unweighted_net:
        return (a, b) if a.unweighted_net > b.unweighted_net else (b, a)
    if a.exact_hits != b.exact_hits:
        return (a, b) if a.exact_hits > b.exact_hits else (b, a)
    return (None, None)
