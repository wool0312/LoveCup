"""API 路由（对应 PRD §7 页面流程 / §8 状态流程 / §9 异常处理）。"""
from __future__ import annotations

import datetime as dt
import json
import uuid
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..core.stages import stage_points
from ..core.stages import Stage as CoreStage
from ..core.timeutil import is_match_locked, lock_time_for_match, match_day_of, now_utc, to_beijing
from ..models import entities as e
from ..models.base import SessionLocal
from ..schemas.schemas import (
    GameCreate,
    OddsSubmit,
    PredictionSubmit,
)
from ..services import settlement as settle
from ..services.match_sync import populate_matches

router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}"


def _audit(db: Session, *, entity: str, entity_id: str, actor: str, action: str,
           before=None, after=None, reason: Optional[str] = None) -> None:
    db.add(e.AuditLog(
        entity=entity, entity_id=entity_id, actor=actor, action=action,
        before=json.dumps(before, ensure_ascii=False) if before is not None else None,
        after=json.dumps(after, ensure_ascii=False) if after is not None else None,
        reason=reason,
    ))


def _get_match(db: Session, match_id: str) -> e.Match:
    m = db.get(e.Match, match_id)
    if m is None:
        raise HTTPException(404, "比赛不存在")
    return m


# ── 开局设置（PRD §7.1）──────────────────────────────────

@router.post("/games")
def create_game(payload: GameCreate, db: Session = Depends(get_db)):
    game_id = payload.custom_id.strip() if payload.custom_id and payload.custom_id.strip() else _new_id("g")
    if db.get(e.Game, game_id):
        raise HTTPException(409, f"对局 ID「{game_id}」已存在，请换一个")
    game = e.Game(
        id=game_id,
        player1_id=_new_id("p"),
        player2_id=_new_id("p"),
        player1_name=payload.player1_name,
        player2_name=payload.player2_name,
        japan_budget_cny=payload.japan_budget_cny,
        rule_version="v0.5",
    )
    db.add(game)
    db.flush()
    match_count = populate_matches(db, game.id)
    db.commit()
    result = _game_dict(game)
    result["matches_created"] = match_count
    return result


def _game_dict(g: e.Game) -> dict:
    return {
        "id": g.id,
        "season": g.season,
        "rule_version": g.rule_version,
        "japan_budget_cny": str(g.japan_budget_cny),
        "status": g.status.value,
        "players": [
            {"id": g.player1_id, "name": g.player1_name},
            {"id": g.player2_id, "name": g.player2_name},
        ],
    }


@router.get("/games/{game_id}")
def get_game(game_id: str, db: Session = Depends(get_db)):
    g = db.get(e.Game, game_id)
    if g is None:
        raise HTTPException(404, "对局不存在")
    return _game_dict(g)


@router.delete("/games/{game_id}")
def delete_game(game_id: str, db: Session = Depends(get_db)):
    g = db.get(e.Game, game_id)
    if g is None:
        raise HTTPException(404, "对局不存在")
    matches = list(db.scalars(select(e.Match).where(e.Match.game_id == game_id)))
    match_ids = [m.id for m in matches]
    if match_ids:
        db.query(e.MatchScore).filter(e.MatchScore.match_id.in_(match_ids)).delete(synchronize_session=False)
        db.query(e.Prediction).filter(e.Prediction.match_id.in_(match_ids)).delete(synchronize_session=False)
        db.query(e.OddsSnapshot).filter(e.OddsSnapshot.match_id.in_(match_ids)).delete(synchronize_session=False)
    db.query(e.Match).filter_by(game_id=game_id).delete()
    db.query(e.RoundSummary).filter_by(game_id=game_id).delete()
    db.query(e.FinalResult).filter_by(game_id=game_id).delete()
    db.delete(g)
    db.commit()
    return {"deleted": game_id}


# ── 比赛查询 ──────────────────────────────────────────────

def _match_dict(db: Session, m: e.Match) -> dict:
    odds = m.odds
    preds = list(db.scalars(select(e.Prediction).where(e.Prediction.match_id == m.id)))
    sp = stage_points(CoreStage(m.stage.value))
    return {
        "id": m.id,
        "stage": m.stage.value,
        "round": m.round.value,
        "home_team": m.home_team,
        "away_team": m.away_team,
        "kickoff_at": m.kickoff_at.isoformat(),
        "kickoff_beijing": to_beijing(m.kickoff_at).isoformat(),
        "match_day": m.match_day.isoformat(),
        "status": m.status.value,
        "is_final": sp.is_final,
        "lock_time_beijing": to_beijing(lock_time_for_match(m.kickoff_at)).isoformat(),
        "locked": is_match_locked(m.kickoff_at),
        "home_goals": m.home_goals,
        "away_goals": m.away_goals,
        "advanced_team": m.advanced_team.value if m.advanced_team else None,
        "stage_points": {"w": str(sp.w), "gd": str(sp.gd), "sc": str(sp.sc), "full": str(sp.full)},
        "odds": None if odds is None else {
            "home_odds": str(odds.home_odds) if odds.home_odds is not None else None,
            "draw_odds": str(odds.draw_odds) if odds.draw_odds is not None else None,
            "away_odds": str(odds.away_odds) if odds.away_odds is not None else None,
            "available": odds.available,
            "source": odds.source,
            "recorded_by": odds.recorded_by,
        },
        "predictions": [_pred_dict(p) for p in preds],
    }


def _pred_dict(p: e.Prediction) -> dict:
    return {
        "player_id": p.player_id,
        "wdl": p.wdl.value,
        "has_gd": p.has_gd,
        "sgd": p.sgd,
        "has_score": p.has_score,
        "pred_home": p.pred_home,
        "pred_away": p.pred_away,
        "use_double": p.use_double,
        "locked_at": p.locked_at.isoformat() if p.locked_at else None,
    }


@router.get("/games/{game_id}/matches")
def list_matches(game_id: str, match_day: Optional[str] = None, db: Session = Depends(get_db)):
    q = select(e.Match).where(e.Match.game_id == game_id)
    if match_day:
        q = q.where(e.Match.match_day == dt.date.fromisoformat(match_day))
    matches = list(db.scalars(q.order_by(e.Match.kickoff_at)))
    return [_match_dict(db, m) for m in matches]


@router.get("/games/{game_id}/match-days")
def list_match_days(game_id: str, db: Session = Depends(get_db)):
    matches = list(db.scalars(select(e.Match).where(e.Match.game_id == game_id)))
    by_day: dict[dt.date, list[e.Match]] = {}
    for m in matches:
        by_day.setdefault(m.match_day, []).append(m)
    # 按场锁定后，比赛日不再有统一锁定时刻；🔒 表示该日所有比赛均已锁定。
    return [
        {
            "match_day": d.isoformat(),
            "locked": all(is_match_locked(m.kickoff_at) for m in by_day[d]),
        }
        for d in sorted(by_day)
    ]


# ── 预测录入（PRD §7.2）──────────────────────────────────

@router.post("/matches/{match_id}/predictions")
def submit_prediction(match_id: str, payload: PredictionSubmit, db: Session = Depends(get_db)):
    m = _get_match(db, match_id)
    if is_match_locked(m.kickoff_at):
        raise HTTPException(409, "已过锁定时刻（开赛前 1 小时），预测只读")
    if m.status in (e.MatchStatus.VOID, e.MatchStatus.SETTLED):
        raise HTTPException(409, f"比赛状态为「{m.status.value}」，不可修改预测")

    if payload.has_score and (payload.pred_home is None or payload.pred_away is None):
        raise HTTPException(422, "选择精确比分时必须填写双方比分")

    sp = stage_points(CoreStage(m.stage.value))
    use_double = payload.use_double
    if use_double:
        if sp.is_final:
            raise HTTPException(422, "决赛禁用 Double")
        if m.odds is None or not m.odds.available:
            raise HTTPException(422, "该场赔率缺失，不可使用 Double")
        # 每名玩家每个比赛日至多一场 Double（PRD §7.2）
        dup = db.scalar(
            select(e.Prediction)
            .join(e.Match, e.Match.id == e.Prediction.match_id)
            .where(
                e.Match.game_id == m.game_id,
                e.Match.match_day == m.match_day,
                e.Prediction.player_id == payload.player_id,
                e.Prediction.use_double.is_(True),
                e.Prediction.match_id != m.id,
            )
        )
        if dup:
            raise HTTPException(409, "当日已有一场使用 Double，每个比赛日至多一场")

    # 精确比分自动推导净胜球
    has_gd = payload.has_gd
    sgd = payload.sgd
    if payload.has_score:
        has_gd = True
        sgd = payload.pred_home - payload.pred_away

    existing = db.scalar(
        select(e.Prediction).where(
            e.Prediction.match_id == match_id,
            e.Prediction.player_id == payload.player_id,
        )
    )
    if existing:
        existing.wdl = payload.wdl
        existing.has_gd = has_gd
        existing.sgd = sgd
        existing.has_score = payload.has_score
        existing.pred_home = payload.pred_home
        existing.pred_away = payload.pred_away
        existing.use_double = use_double
        existing.submitted_at = now_utc().replace(tzinfo=None)
        pred = existing
    else:
        pred = e.Prediction(
            match_id=match_id,
            player_id=payload.player_id,
            wdl=payload.wdl,
            has_gd=has_gd,
            sgd=sgd,
            has_score=payload.has_score,
            pred_home=payload.pred_home,
            pred_away=payload.pred_away,
            use_double=use_double,
        )
        db.add(pred)
    db.commit()
    return _pred_dict(pred)


# ── 赔率录入（PRD §7.3）──────────────────────────────────

@router.post("/matches/{match_id}/odds")
def submit_odds(match_id: str, payload: OddsSubmit, db: Session = Depends(get_db)):
    m = _get_match(db, match_id)
    if is_match_locked(m.kickoff_at):
        raise HTTPException(409, "已过锁定时刻（开赛前 1 小时），赔率不可修改")

    odds = m.odds
    if odds is None:
        odds = e.OddsSnapshot(match_id=match_id, recorded_by=payload.recorded_by)
        db.add(odds)
    odds.home_odds = payload.home_odds
    odds.draw_odds = payload.draw_odds
    odds.away_odds = payload.away_odds
    odds.available = payload.available
    odds.source = payload.source
    odds.recorded_by = payload.recorded_by
    odds.recorded_at = now_utc().replace(tzinfo=None)
    db.commit()
    return _match_dict(db, m)


# ── 统一锁定（PRD §7.3 / §8.2）──────────────────────────

@router.post("/matches/{match_id}/lock")
def lock_match(match_id: str, db: Session = Depends(get_db)):
    m = _get_match(db, match_id)
    return _do_lock(db, m)


def _do_lock(db: Session, m: e.Match) -> dict:
    if m.status == e.MatchStatus.PENDING:
        m.status = e.MatchStatus.LOCKED
        m.locked_at = now_utc().replace(tzinfo=None)
        for p in db.scalars(select(e.Prediction).where(e.Prediction.match_id == m.id)):
            p.locked_at = m.locked_at
        db.commit()
    return _match_dict(db, m)


# ── 异常处理（PRD §9）────────────────────────────────────

@router.post("/matches/{match_id}/void")
def void_match(match_id: str, actor: str, reason: str = "", db: Session = Depends(get_db)):
    m = _get_match(db, match_id)
    before = {"status": m.status.value}
    m.status = e.MatchStatus.VOID
    db.query(e.MatchScore).filter_by(match_id=match_id).delete()
    _audit(db, entity="Match", entity_id=m.id, actor=actor, action="作废比赛",
           before=before, after={"status": m.status.value}, reason=reason)
    db.commit()
    settle.recompute_standings(db, m.game_id)
    return _match_dict(db, m)


@router.post("/matches/{match_id}/postpone")
def postpone_match(match_id: str, actor: str, new_kickoff: str, reason: str = "",
                   db: Session = Depends(get_db)):
    m = _get_match(db, match_id)
    before = {"kickoff_at": m.kickoff_at.isoformat(), "match_day": m.match_day.isoformat(),
              "status": m.status.value}
    kickoff = dt.datetime.fromisoformat(new_kickoff)
    if kickoff.tzinfo is not None:
        kickoff = kickoff.astimezone(dt.timezone.utc).replace(tzinfo=None)
    m.kickoff_at = kickoff
    m.match_day = match_day_of(kickoff)
    m.status = e.MatchStatus.POSTPONED
    _audit(db, entity="Match", entity_id=m.id, actor=actor, action="延期改期",
           before=before, after={"kickoff_at": m.kickoff_at.isoformat(),
                                 "match_day": m.match_day.isoformat()}, reason=reason)
    db.commit()
    return _match_dict(db, m)


# ── 实时积分 / 历史 / 导出（PRD §7.4 / §7.5 / §7.6）─────

@router.get("/games/{game_id}/standings")
def get_standings(game_id: str, db: Session = Depends(get_db)):
    if db.get(e.Game, game_id) is None:
        raise HTTPException(404, "对局不存在")
    return settle.recompute_standings(db, game_id)


@router.get("/games/{game_id}/history")
def get_history(game_id: str, db: Session = Depends(get_db)):
    matches = list(db.scalars(
        select(e.Match).where(e.Match.game_id == game_id).order_by(e.Match.kickoff_at)))
    out = []
    for m in matches:
        md = _match_dict(db, m)
        scores = list(db.scalars(select(e.MatchScore).where(e.MatchScore.match_id == m.id)))
        md["scores"] = [{
            "player_id": s.player_id, "mode": s.mode.value, "odds_used": str(s.odds_used) if s.odds_used else None,
            "score": str(s.score), "manual_override": s.manual_override,
            "breakdown": json.loads(s.breakdown) if s.breakdown else None,
        } for s in scores]
        out.append(md)
    return out


@router.get("/games/{game_id}/audit")
def get_audit(game_id: str, db: Session = Depends(get_db)):
    logs = list(db.scalars(select(e.AuditLog).order_by(e.AuditLog.at.desc())))
    return [{
        "entity": l.entity, "entity_id": l.entity_id, "actor": l.actor, "action": l.action,
        "before": json.loads(l.before) if l.before else None,
        "after": json.loads(l.after) if l.after else None,
        "reason": l.reason, "at": l.at.isoformat(),
    } for l in logs]


@router.get("/games/{game_id}/export")
def export_game(game_id: str, db: Session = Depends(get_db)):
    g = db.get(e.Game, game_id)
    if g is None:
        raise HTTPException(404, "对局不存在")
    return {
        "game": _game_dict(g),
        "matches": get_history(game_id, db),
        "standings": settle.recompute_standings(db, game_id),
        "audit": get_audit(game_id, db),
        "exported_at": now_utc().isoformat(),
    }


@router.get("/games/{game_id}/export.csv")
def export_game_csv(game_id: str, db: Session = Depends(get_db)):
    import csv
    import io

    from fastapi.responses import StreamingResponse

    g = db.get(e.Game, game_id)
    if g is None:
        raise HTTPException(404, "对局不存在")
    name = {g.player1_id: g.player1_name, g.player2_id: g.player2_name}

    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["比赛日", "阶段", "主队", "客队", "比分", "晋级方", "玩家",
                "模式", "所用赔率", "得分", "人工改分"])
    matches = list(db.scalars(
        select(e.Match).where(e.Match.game_id == game_id).order_by(e.Match.kickoff_at)))
    for m in matches:
        score_str = f"{m.home_goals}:{m.away_goals}" if m.home_goals is not None else ""
        for s in db.scalars(select(e.MatchScore).where(e.MatchScore.match_id == m.id)):
            w.writerow([
                m.match_day.isoformat(), m.stage.value, m.home_team, m.away_team,
                score_str, m.advanced_team.value if m.advanced_team else "",
                name.get(s.player_id, s.player_id), s.mode.value,
                str(s.odds_used) if s.odds_used else "", str(s.score),
                "是" if s.manual_override else "",
            ])
    buf.seek(0)
    filename = f"lovecup_{game_id}.csv"
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
