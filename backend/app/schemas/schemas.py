"""API 出入参模型（Pydantic v2）。"""
from __future__ import annotations

import datetime as dt
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from ..models.entities import Stage, WDL


class GameCreate(BaseModel):
    player1_name: str = Field(min_length=1)
    player2_name: str = Field(min_length=1)
    japan_budget_cny: Decimal = Decimal("1000")

    @field_validator("japan_budget_cny")
    @classmethod
    def budget_non_negative(cls, v: Decimal) -> Decimal:
        if v < 0:
            raise ValueError("预算必须为非负数")
        return v


class MatchCreate(BaseModel):
    stage: Stage
    home_team: str = Field(min_length=1)
    away_team: str = Field(min_length=1)
    kickoff_at: dt.datetime  # UTC


class PredictionSubmit(BaseModel):
    player_id: str
    wdl: WDL                       # 必填
    has_gd: bool = False
    sgd: Optional[int] = None
    has_score: bool = False
    pred_home: Optional[int] = None
    pred_away: Optional[int] = None
    use_double: bool = False


class OddsSubmit(BaseModel):
    recorded_by: str
    home_odds: Optional[Decimal] = None
    draw_odds: Optional[Decimal] = None
    away_odds: Optional[Decimal] = None
    available: bool = True
    source: Optional[str] = None

    @field_validator("home_odds", "draw_odds", "away_odds")
    @classmethod
    def odds_at_least_one(cls, v: Optional[Decimal]) -> Optional[Decimal]:
        if v is not None and v < Decimal("1.00"):
            raise ValueError("赔率必须 ≥ 1.00")
        return v


class ResultSubmit(BaseModel):
    home_goals: int = Field(ge=0)       # 常规+加时（不含点球）
    away_goals: int = Field(ge=0)
    advanced_team: Optional[WDL] = None  # 淘汰赛晋级方（含点球）
    actor: str


class ManualOverride(BaseModel):
    player_id: str
    score: Decimal
    reason: str = Field(min_length=1)
    actor: str
