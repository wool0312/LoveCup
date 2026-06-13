"""阶段基础分、轮次划分与权重（对应 PRD §4.1 / §4.6）。

所有数值用 Decimal，避免浮点误差。
"""
from __future__ import annotations

import enum
from dataclasses import dataclass
from decimal import Decimal
from typing import Dict, List


class Stage(str, enum.Enum):
    """比赛阶段（PRD §3.2 / §4.1）。"""

    GROUP = "小组赛"
    R32 = "32强"
    R16 = "16强"
    QF = "8强"
    SF = "半决赛"
    THIRD = "三四名"
    FINAL = "决赛"


class Round(str, enum.Enum):
    """六个结算轮次（PRD §4.6）。"""

    R1 = "第1轮"
    R2 = "第2轮"
    R3 = "第3轮"
    R4 = "第4轮"
    R5 = "第5轮"
    R6 = "第6轮"


@dataclass(frozen=True)
class StagePoints:
    """某阶段的基础分值与 Double 本金（PRD §4.1）。"""

    w: Decimal       # 胜平负
    gd: Decimal      # 净胜球
    sc: Decimal      # 精确比分
    full: Decimal    # 满分（= w + gd + sc）
    stake: Decimal   # Double 本金（= w）
    is_final: bool   # 决赛禁用 Double


def _d(value: int) -> Decimal:
    return Decimal(value)


# PRD §4.1 阶段与基础分值表
STAGE_POINTS: Dict[Stage, StagePoints] = {
    Stage.GROUP: StagePoints(_d(1), _d(1), _d(2), _d(4), _d(1), is_final=False),
    Stage.R32:   StagePoints(_d(2), _d(2), _d(4), _d(8), _d(2), is_final=False),
    Stage.R16:   StagePoints(_d(4), _d(4), _d(8), _d(16), _d(4), is_final=False),
    Stage.QF:    StagePoints(_d(8), _d(8), _d(16), _d(32), _d(8), is_final=False),
    Stage.SF:    StagePoints(_d(12), _d(12), _d(24), _d(48), _d(12), is_final=False),
    Stage.THIRD: StagePoints(_d(4), _d(4), _d(8), _d(16), _d(4), is_final=False),
    # 决赛禁用 Double：stake 不参与计算，标记 is_final=True
    Stage.FINAL: StagePoints(_d(24), _d(24), _d(48), _d(96), _d(24), is_final=True),
}


# PRD §4.6 阶段 -> 轮次映射
STAGE_TO_ROUND: Dict[Stage, Round] = {
    Stage.GROUP: Round.R1,
    Stage.R32: Round.R2,
    Stage.R16: Round.R3,
    Stage.QF: Round.R4,
    Stage.SF: Round.R5,
    Stage.THIRD: Round.R5,   # 半决赛 + 三四名 同属第 5 轮
    Stage.FINAL: Round.R6,
}


# PRD §4.6 轮次权重（百分比，用 Decimal 精确表示）
ROUND_WEIGHT: Dict[Round, Decimal] = {
    Round.R1: Decimal("0.07"),
    Round.R2: Decimal("0.15"),
    Round.R3: Decimal("0.16"),
    Round.R4: Decimal("0.18"),
    Round.R5: Decimal("0.20"),
    Round.R6: Decimal("0.24"),
}


def stage_points(stage: Stage) -> StagePoints:
    return STAGE_POINTS[stage]


def round_of(stage: Stage) -> Round:
    return STAGE_TO_ROUND[stage]


def weight_of(rnd: Round) -> Decimal:
    return ROUND_WEIGHT[rnd]


def stages_in_round(rnd: Round) -> List[Stage]:
    return [s for s, r in STAGE_TO_ROUND.items() if r == rnd]
