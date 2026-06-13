"""数据模型（对应 PRD §3）。

金额/积分一律用 DecimalText（定点小数文本存储）。
枚举值直接采用 PRD 中文术语，便于对照与导出。
"""
from __future__ import annotations

import datetime as dt
import enum
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, DecimalText


# ── 枚举 ──────────────────────────────────────────────────

class GameStatus(str, enum.Enum):
    ONGOING = "进行中"
    FINISHED = "已结束"


class Stage(str, enum.Enum):
    GROUP = "小组赛"
    R32 = "32强"
    R16 = "16强"
    QF = "8强"
    SF = "半决赛"
    THIRD = "三四名"
    FINAL = "决赛"


class RoundName(str, enum.Enum):
    R1 = "第1轮"
    R2 = "第2轮"
    R3 = "第3轮"
    R4 = "第4轮"
    R5 = "第5轮"
    R6 = "第6轮"


class MatchStatus(str, enum.Enum):
    PENDING = "待预测"
    LOCKED = "已锁定"
    SETTLED = "已结算"
    VOID = "作废"
    POSTPONED = "延期"


class WDL(str, enum.Enum):
    HOME = "主胜"
    DRAW = "平"
    AWAY = "客胜"


class ScoreMode(str, enum.Enum):
    NORMAL = "普通"
    DOUBLE = "Double"


# ── 实体 ──────────────────────────────────────────────────

class Game(Base):
    """对局（PRD §3.1）。"""

    __tablename__ = "games"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    season: Mapped[int] = mapped_column(Integer, default=2026)
    player1_id: Mapped[str] = mapped_column(String)
    player2_id: Mapped[str] = mapped_column(String)
    player1_name: Mapped[str] = mapped_column(String)
    player2_name: Mapped[str] = mapped_column(String)
    player1_pin_hash: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    player2_pin_hash: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    rule_version: Mapped[str] = mapped_column(String, default="v0.5")
    japan_budget_cny: Mapped[Decimal] = mapped_column(DecimalText, default=Decimal("1000"))
    admin_pin_hash: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    status: Mapped[GameStatus] = mapped_column(SAEnum(GameStatus), default=GameStatus.ONGOING)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)


class Match(Base):
    """比赛（PRD §3.2）。"""

    __tablename__ = "matches"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    game_id: Mapped[str] = mapped_column(ForeignKey("games.id"))
    stage: Mapped[Stage] = mapped_column(SAEnum(Stage))
    round: Mapped[RoundName] = mapped_column(SAEnum(RoundName))
    home_team: Mapped[str] = mapped_column(String)
    away_team: Mapped[str] = mapped_column(String)
    kickoff_at: Mapped[dt.datetime] = mapped_column(DateTime)  # 存 UTC
    match_day: Mapped[dt.date] = mapped_column(Date)           # 归属比赛日（北京时间锚定）
    status: Mapped[MatchStatus] = mapped_column(SAEnum(MatchStatus), default=MatchStatus.PENDING)
    locked_at: Mapped[Optional[dt.datetime]] = mapped_column(DateTime, nullable=True)

    # 结算后写入：常规+加时比分（不含点球）
    home_goals: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    away_goals: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    # 淘汰赛最终晋级方（含点球），用于胜平负判定
    advanced_team: Mapped[Optional[WDL]] = mapped_column(SAEnum(WDL), nullable=True)

    odds: Mapped[Optional["OddsSnapshot"]] = relationship(back_populates="match", uselist=False)
    predictions: Mapped[list["Prediction"]] = relationship(back_populates="match")


class OddsSnapshot(Base):
    """赔率快照（PRD §3.3）。"""

    __tablename__ = "odds_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    match_id: Mapped[str] = mapped_column(ForeignKey("matches.id"), unique=True)
    home_odds: Mapped[Optional[Decimal]] = mapped_column(DecimalText, nullable=True)
    draw_odds: Mapped[Optional[Decimal]] = mapped_column(DecimalText, nullable=True)
    away_odds: Mapped[Optional[Decimal]] = mapped_column(DecimalText, nullable=True)
    recorded_by: Mapped[str] = mapped_column(String)
    recorded_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)
    available: Mapped[bool] = mapped_column(Boolean, default=True)
    source: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    match: Mapped["Match"] = relationship(back_populates="odds")


class Prediction(Base):
    """预测（PRD §3.4）。"""

    __tablename__ = "predictions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    match_id: Mapped[str] = mapped_column(ForeignKey("matches.id"))
    player_id: Mapped[str] = mapped_column(String)
    wdl: Mapped[WDL] = mapped_column(SAEnum(WDL))
    has_gd: Mapped[bool] = mapped_column(Boolean, default=False)
    sgd: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    has_score: Mapped[bool] = mapped_column(Boolean, default=False)
    pred_home: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    pred_away: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    use_double: Mapped[bool] = mapped_column(Boolean, default=False)
    bound_home_odds: Mapped[Optional[Decimal]] = mapped_column(DecimalText, nullable=True)
    bound_draw_odds: Mapped[Optional[Decimal]] = mapped_column(DecimalText, nullable=True)
    bound_away_odds: Mapped[Optional[Decimal]] = mapped_column(DecimalText, nullable=True)
    bound_odds_source: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    submitted_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)
    locked_at: Mapped[Optional[dt.datetime]] = mapped_column(DateTime, nullable=True)

    match: Mapped["Match"] = relationship(back_populates="predictions")


class MatchScore(Base):
    """单场得分（PRD §3.5）。breakdown 存各项明细 JSON，便于复核。"""

    __tablename__ = "match_scores"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    match_id: Mapped[str] = mapped_column(ForeignKey("matches.id"))
    player_id: Mapped[str] = mapped_column(String)
    mode: Mapped[ScoreMode] = mapped_column(SAEnum(ScoreMode))
    odds_used: Mapped[Optional[Decimal]] = mapped_column(DecimalText, nullable=True)
    breakdown: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON 明细
    score: Mapped[Decimal] = mapped_column(DecimalText)
    manual_override: Mapped[bool] = mapped_column(Boolean, default=False)
    override_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class RoundSummary(Base):
    """轮次汇总（PRD §3.5）。"""

    __tablename__ = "round_summaries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    game_id: Mapped[str] = mapped_column(ForeignKey("games.id"))
    round: Mapped[RoundName] = mapped_column(SAEnum(RoundName))
    player_id: Mapped[str] = mapped_column(String)
    net_score: Mapped[Decimal] = mapped_column(DecimalText)
    weight: Mapped[Decimal] = mapped_column(DecimalText)
    weighted_score: Mapped[Decimal] = mapped_column(DecimalText)
    round_champion: Mapped[bool] = mapped_column(Boolean, default=False)


class FinalResult(Base):
    """最终结果（PRD §3.5）。"""

    __tablename__ = "final_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    game_id: Mapped[str] = mapped_column(ForeignKey("games.id"))
    player_id: Mapped[str] = mapped_column(String)
    final_score: Mapped[Decimal] = mapped_column(DecimalText)
    rank: Mapped[int] = mapped_column(Integer)
    is_champion: Mapped[bool] = mapped_column(Boolean, default=False)
    blowout: Mapped[bool] = mapped_column(Boolean, default=False)


class AuditLog(Base):
    """操作留痕（PRD §3.5 / §9）。改期、改分等异常处理必须留痕。"""

    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    entity: Mapped[str] = mapped_column(String)
    entity_id: Mapped[str] = mapped_column(String)
    actor: Mapped[str] = mapped_column(String)
    action: Mapped[str] = mapped_column(String)
    before: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    after: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)
