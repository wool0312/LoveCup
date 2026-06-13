import type { Game, Match, MatchDay, Standings } from "./types";

const BASE = import.meta.env.VITE_API_BASE ?? "/api";

async function req<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    let detail = `${res.status}`;
    try {
      const body = await res.json();
      detail = body.detail ? JSON.stringify(body.detail) : detail;
    } catch {
      /* ignore */
    }
    throw new Error(detail);
  }
  return res.json() as Promise<T>;
}

export const api = {
  health: () => req<{ status: string }>("/health"),

  createGame: (body: {
    custom_id?: string;
    player1_name: string;
    player2_name: string;
    admin_pin?: string;
    japan_budget_cny?: string;
  }) => req<Game>("/games", { method: "POST", body: JSON.stringify(body) }),

  getGame: (gameId: string) => req<Game>(`/games/${gameId}`),

  deleteGame: (gameId: string, adminPin: string) =>
    req(`/games/${gameId}`, { method: "DELETE", body: JSON.stringify({ admin_pin: adminPin }) }),

  listMatchDays: (gameId: string) => req<MatchDay[]>(`/games/${gameId}/match-days`),

  listMatches: (gameId: string, matchDay?: string) =>
    req<Match[]>(
      `/games/${gameId}/matches${matchDay ? `?match_day=${matchDay}` : ""}`
    ),

  submitPrediction: (
    matchId: string,
    body: {
      player_id: string;
      wdl: string;
      has_gd?: boolean;
      sgd?: number | null;
      has_score?: boolean;
      pred_home?: number | null;
      pred_away?: number | null;
      use_double?: boolean;
    }
  ) =>
    req(`/matches/${matchId}/predictions`, {
      method: "POST",
      body: JSON.stringify(body),
    }),

  submitOdds: (
    matchId: string,
    body: {
      recorded_by: string;
      home_odds?: string | null;
      draw_odds?: string | null;
      away_odds?: string | null;
      available?: boolean;
      source?: string | null;
      admin_pin?: string;
    }
  ) => req<Match>(`/matches/${matchId}/odds`, { method: "POST", body: JSON.stringify(body) }),

  standings: (gameId: string) => req<Standings>(`/games/${gameId}/standings`),

  history: (gameId: string) => req<Match[]>(`/games/${gameId}/history`),

  exportUrl: (gameId: string) => `${BASE}/games/${gameId}/export`,
  exportCsvUrl: (gameId: string) => `${BASE}/games/${gameId}/export.csv`,
};
