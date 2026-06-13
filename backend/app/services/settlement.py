"""结算服务：连接数据库与计分核心，写入 MatchScore / RoundSummary / FinalResult。

可复核要求（PRD §10）：每场得分都附带 breakdown 明细 JSON，记录每一项怎么算出来的。
"""
from __future__ import annotations

import json
from decimal import Decimal
from typing import Dict, List, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..core import scoring as sc
from ..core import settlement as st
from ..core.stages import Round as CoreRound
from ..core.stages import Stage as CoreStage
from ..core.stages import round_of, stage_points, weight_of
from ..models import entities as e


# ── 枚举转换（DB 枚举 ↔ 核心枚举，按值映射）──────────────────

def _core_wdl(w: e.WDL) -> sc.WDL:
    return sc.WDL(w.value)


def _core_stage(s: e.Stage) -> CoreStage:
    return CoreStage(s.value)


def _build_result(match: e.Match) -> sc.MatchResult:
    """由比赛结果构造核心层 MatchResult（处理淘汰赛点球口径）。"""
    home, away = match.home_goals, match.away_goals
    if match.stage == e.Stage.GROUP:
        return sc.MatchResult.from_goals(home, away)
    # 淘汰赛：胜负看晋级方（含点球），净胜球/比分看加时结束比分
    advanced_home = match.advanced_team == e.WDL.HOME
    return sc.MatchResult.from_knockout(home, away, advanced_home=advanced_home)


def _build_prediction(p: e.Prediction) -> sc.Prediction:
    return sc.Prediction(
        wdl=_core_wdl(p.wdl),
        has_gd=p.has_gd,
        sgd=p.sgd,
        has_score=p.has_score,
        pred_home=p.pred_home,
        pred_away=p.pred_away,
        use_double=p.use_double,
    )


def _odds_for(wdl: e.WDL, pred: e.Prediction, odds: Optional[e.OddsSnapshot]) -> Optional[Decimal]:
    bound = {
        e.WDL.HOME: pred.bound_home_odds,
        e.WDL.DRAW: pred.bound_draw_odds,
        e.WDL.AWAY: pred.bound_away_odds,
    }[wdl]
    if bound is not None:
        return bound
    # 兼容旧预测：历史数据没有绑定赔率时，回退到比赛当前赔率。
    if odds is None or not odds.available:
        return None
    return {
        e.WDL.HOME: odds.home_odds,
        e.WDL.DRAW: odds.draw_odds,
        e.WDL.AWAY: odds.away_odds,
    }[wdl]


def compute_match_score(
    match: e.Match, pred: Optional[e.Prediction], odds: Optional[e.OddsSnapshot]
) -> Tuple[Decimal, e.ScoreMode, Optional[Decimal], dict]:
    """复算单场得分，返回 (score, mode, odds_used, breakdown)。纯计算，不写库。"""
    sp = stage_points(_core_stage(match.stage))
    result = _build_result(match)

    if pred is None:
        return Decimal(0), e.ScoreMode.NORMAL, None, {"reason": "未提交预测，计 0 分"}

    core_pred = _build_prediction(pred)
    odds_used = _odds_for(pred.wdl, pred, odds)
    odds_available = odds_used is not None

    use_double = pred.use_double and odds_available and not sp.is_final
    mode = e.ScoreMode.DOUBLE if use_double else e.ScoreMode.NORMAL

    wdl_correct = core_pred.wdl == result.wdl
    gd_hit = core_pred.has_gd and core_pred.sgd == result.sgd
    score_hit = (
        core_pred.has_score
        and core_pred.pred_home == result.home
        and core_pred.pred_away == result.away
    )

    if use_double:
        score = sc.score_double(core_pred, result, sp, odds_used)
        breakdown = {
            "mode": "Double",
            "stake": str(sp.stake),
            "odds": str(odds_used),
            "odds_source": pred.bound_odds_source or (odds.source if odds else None),
            "wdl_correct": wdl_correct,
            "base": str(sp.stake * (odds_used - 1)) if wdl_correct else str(-sp.stake),
            "gd_bonus": str(sp.gd) if gd_hit else "0",
            "score_bonus": str(sp.sc) if score_hit else "0",
            "total": str(score),
        }
    else:
        score = sc.score_normal(core_pred, result, sp)
        breakdown = {
            "mode": "普通",
            "wdl_correct": wdl_correct,
            "wdl_points": str(sp.w) if wdl_correct else "0",
            "gd_bonus": str(sp.gd) if gd_hit else "0",
            "score_bonus": str(sp.sc) if score_hit else "0",
            "total": str(score),
        }
        odds_used = None

    return score, mode, odds_used, breakdown


def settle_match(db: Session, match: e.Match) -> List[e.MatchScore]:
    """结算一场比赛：为两名玩家各算一条 MatchScore（覆盖旧的非人工记录）。"""
    game = db.get(e.Game, match.game_id)
    players = [game.player1_id, game.player2_id]
    odds = match.odds

    results: List[e.MatchScore] = []
    for player_id in players:
        pred = db.scalar(
            select(e.Prediction).where(
                e.Prediction.match_id == match.id,
                e.Prediction.player_id == player_id,
            )
        )
        score, mode, odds_used, breakdown = compute_match_score(match, pred, odds)

        existing = db.scalar(
            select(e.MatchScore).where(
                e.MatchScore.match_id == match.id,
                e.MatchScore.player_id == player_id,
            )
        )
        if existing and existing.manual_override:
            results.append(existing)  # 人工改分保留，不覆盖
            continue

        if existing:
            existing.mode = mode
            existing.odds_used = odds_used
            existing.breakdown = json.dumps(breakdown, ensure_ascii=False)
            existing.score = score
            results.append(existing)
        else:
            ms = e.MatchScore(
                match_id=match.id,
                player_id=player_id,
                mode=mode,
                odds_used=odds_used,
                breakdown=json.dumps(breakdown, ensure_ascii=False),
                score=score,
            )
            db.add(ms)
            results.append(ms)

    match.status = e.MatchStatus.SETTLED
    db.commit()
    return results


# ── 轮次与最终结算 ────────────────────────────────────────

def _player_match_scores(db: Session, game_id: str, player_id: str) -> List[e.MatchScore]:
    return list(
        db.scalars(
            select(e.MatchScore)
            .join(e.Match, e.Match.id == e.MatchScore.match_id)
            .where(e.Match.game_id == game_id, e.MatchScore.player_id == player_id)
        )
    )


def _round_nets(db: Session, game_id: str, player_id: str) -> Dict[CoreRound, Decimal]:
    """按轮次汇总该玩家净积分（仅计已结算且非作废的比赛）。"""
    nets: Dict[CoreRound, Decimal] = {r: Decimal(0) for r in CoreRound}
    rows = db.execute(
        select(e.Match.stage, e.MatchScore.score)
        .join(e.MatchScore, e.MatchScore.match_id == e.Match.id)
        .where(
            e.Match.game_id == game_id,
            e.MatchScore.player_id == player_id,
            e.Match.status == e.MatchStatus.SETTLED,
        )
    ).all()
    for stage, score in rows:
        rnd = round_of(_core_stage(stage))
        nets[rnd] += score
    return nets


def _exact_hits(db: Session, game_id: str, player_id: str) -> int:
    """精确比分命中次数（同分次级比较用，PRD §4.7）。"""
    count = 0
    for ms in _player_match_scores(db, game_id, player_id):
        if ms.breakdown:
            b = json.loads(ms.breakdown)
            if b.get("score_bonus", "0") not in ("0", "0.00"):
                count += 1
    return count


def recompute_standings(db: Session, game_id: str) -> dict:
    """重算轮次汇总与最终结果，写入 RoundSummary / FinalResult，返回展示数据。"""
    game = db.get(e.Game, game_id)
    standings = {}

    for player_id in (game.player1_id, game.player2_id):
        nets = _round_nets(db, game_id, player_id)
        fscore = st.final_score(nets)
        unweighted = sum(nets.values(), Decimal(0))
        hits = _exact_hits(db, game_id, player_id)

        # 重写 RoundSummary
        db.query(e.RoundSummary).filter_by(game_id=game_id, player_id=player_id).delete()
        for rnd, net in nets.items():
            w = weight_of(rnd)
            db.add(
                e.RoundSummary(
                    game_id=game_id,
                    round=e.RoundName(rnd.value),
                    player_id=player_id,
                    net_score=net,
                    weight=w,
                    weighted_score=net * w,
                )
            )

        standings[player_id] = st.PlayerStanding(
            player_id=player_id,
            final_score=fscore,
            unweighted_net=unweighted,
            exact_hits=hits,
        )

    a = standings[game.player1_id]
    b = standings[game.player2_id]
    outcome = st.decide_outcome(a, b)

    # 重写 FinalResult
    db.query(e.FinalResult).filter_by(game_id=game_id).delete()
    for ps in (a, b):
        is_champ = ps.player_id in outcome.champion_ids
        rank = 1 if is_champ else 2
        db.add(
            e.FinalResult(
                game_id=game_id,
                player_id=ps.player_id,
                final_score=ps.final_score,
                rank=rank,
                is_champion=is_champ,
                blowout=outcome.blowout and is_champ,
            )
        )
    db.commit()

    return {
        "players": {
            ps.player_id: {
                "final_score": str(st.display_round(ps.final_score)),
                "final_score_raw": str(ps.final_score),
                "unweighted_net": str(ps.unweighted_net),
                "exact_hits": ps.exact_hits,
                "round_nets": {
                    r.value: str(st.display_round(n))
                    for r, n in _round_nets(db, game_id, ps.player_id).items()
                },
            }
            for ps in (a, b)
        },
        "champion_ids": outcome.champion_ids,
        "is_tie": outcome.is_tie,
        "blowout": outcome.blowout,
        "margin_ratio": str(outcome.margin_ratio) if outcome.margin_ratio is not None else None,
    }
