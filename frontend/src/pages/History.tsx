import { useEffect, useState } from "react";
import { api } from "../api";
import type { Game, Match } from "../types";
import { Banner, Card, Pill } from "../ui";

export default function History({ game }: { game: Game }) {
  const [matches, setMatches] = useState<Match[]>([]);
  const nameOf = (id: string) => game.players.find((p) => p.id === id)?.name ?? id;

  useEffect(() => {
    api.history(game.id).then(setMatches);
  }, [game.id]);

  const settled = matches.filter((m) => m.status === "已结算");

  return (
    <div className="space-y-3">
      <div className="flex gap-2">
        <a
          href={api.exportUrl(game.id)}
          target="_blank"
          rel="noreferrer"
          className="flex-1 rounded-xl bg-rose-50 py-2 text-center text-sm font-medium text-brand"
        >
          导出 JSON
        </a>
        <a
          href={api.exportCsvUrl(game.id)}
          className="flex-1 rounded-xl bg-rose-50 py-2 text-center text-sm font-medium text-brand"
        >
          导出 CSV
        </a>
      </div>

      {settled.length === 0 && <Banner tone="info">还没有已结算的比赛。</Banner>}

      {settled.map((m) => (
        <Card key={m.id}>
          <div className="flex items-center justify-between">
            <div className="font-semibold">
              {m.home_team} {m.home_goals}:{m.away_goals} {m.away_team}
            </div>
            <Pill tone="green">{m.stage}</Pill>
          </div>
          <div className="text-xs text-slate-400">
            锁定 {new Date(m.lock_time_beijing).toLocaleString("zh-CN")}
            {m.odds?.available &&
              ` · 赔率快照 ${m.odds.home_odds}/${m.odds.draw_odds}/${m.odds.away_odds}`}
            {m.advanced_team && ` · 晋级 ${m.advanced_team}`}
          </div>

          <div className="mt-2 space-y-2">
            {m.scores?.map((s) => (
              <div key={s.player_id} className="rounded-xl bg-slate-50 p-2">
                <div className="flex items-center justify-between text-sm">
                  <span className="font-medium">
                    {nameOf(s.player_id)}{" "}
                    {s.mode === "Double" && <Pill tone="rose">Double</Pill>}
                    {s.manual_override && <Pill tone="amber">人工改分</Pill>}
                  </span>
                  <span className="font-mono font-semibold">{s.score}</span>
                </div>
                {s.breakdown && (
                  <pre className="mt-1 whitespace-pre-wrap break-all text-[11px] text-slate-500">
                    {Object.entries(s.breakdown)
                      .map(([k, v]) => `${k}: ${v}`)
                      .join("  ·  ")}
                  </pre>
                )}
              </div>
            ))}
          </div>
        </Card>
      ))}
    </div>
  );
}
