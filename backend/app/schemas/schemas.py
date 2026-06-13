"""API 出入参模型（Pydantic v2）。"""
from __future__ import annotations

from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from ..models.entities import WDL


class GameCreate(BaseModel):
    custom_id: Optional[str] = None
    player1_name: str = Field(min_length=1)
    player2_name: str = Field(min_length=1)
    admin_pin: Optional[str] = None
    japan_budget_cny: Decimal = Decimal("1000")

    @field_validator("japan_budget_cny")
    @classmethod
    def budget_non_negative(cls, v: Decimal) -> Decimal:
        if v < 0:
            raise ValueError("预算必须为非负数")
        return v

    @field_validator("admin_pin")
    @classmethod
    def admin_pin_valid(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v.strip() and len(v.strip()) < 4:
            raise ValueError("管理 PIN 至少 4 位")
        return v.strip() if v else None


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
    admin_pin: Optional[str] = None
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


class AdminAction(BaseModel):
    admin_pin: Optional[str] = None
