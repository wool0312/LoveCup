export type WDL = "主胜" | "平" | "客胜";

export interface Player {
  id: string;
  name: string;
}

export interface Game {
  id: string;
  season: number;
  rule_version: string;
  japan_budget_cny: string;
  status: string;
  players: Player[];
}

export interface Odds {
  home_odds: string | null;
  draw_odds: string | null;
  away_odds: string | null;
  available: boolean;
  source: string | null;
  recorded_by: string;
}

export interface Prediction {
  player_id: string;
  wdl: WDL;
  has_gd: boolean;
  sgd: number | null;
  has_score: boolean;
  pred_home: number | null;
  pred_away: number | null;
  use_double: boolean;
  bound_home_odds: string | null;
  bound_draw_odds: string | null;
  bound_away_odds: string | null;
  bound_odds_source: string | null;
  locked_at: string | null;
}

export interface StagePoints {
  w: string;
  gd: string;
  sc: string;
  full: string;
}

export interface ScoreBreakdown {
  player_id: string;
  mode: string;
  odds_used?: string | null;
  score: string;
  manual_override?: boolean;
  breakdown: Record<string, unknown> | null;
}

export interface Match {
  id: string;
  stage: string;
  round: string;
  home_team: string;
  away_team: string;
  kickoff_at: string;
  kickoff_beijing: string;
  match_day: string;
  status: string;
  is_final: boolean;
  lock_time_beijing: string;
  locked: boolean;
  home_goals: number | null;
  away_goals: number | null;
  advanced_team: WDL | null;
  stage_points: StagePoints;
  odds: Odds | null;
  predictions: Prediction[];
  scores?: ScoreBreakdown[];
}

export interface MatchDay {
  match_day: string;
  locked: boolean;
}

export interface PlayerStanding {
  final_score: string;
  final_score_raw: string;
  unweighted_net: string;
  exact_hits: number;
  round_nets: Record<string, string>;
}

export interface Standings {
  players: Record<string, PlayerStanding>;
  champion_ids: string[];
  is_tie: boolean;
  blowout: boolean;
  margin_ratio: string | null;
}
