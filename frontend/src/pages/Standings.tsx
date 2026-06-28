import { useEffect, useState } from "react";
import { api } from "../api";
import type { Game, Standings as StandingsT } from "../types";
import { Banner, Card, Pill } from "../ui";

const ROUNDS = ["第1轮", "第2轮", "第3轮", "第4轮", "第5轮", "第6轮"];
const WEIGHTS: Record<string, string> = {
  第1轮: "7%",
  第2轮: "15%",
  第3轮: "16%",
  第4轮: "18%",
  第5轮: "20%",
  第6轮: "24%",
};

export default function Standings({ game }: { game: Game }) {
  const [data, setData] = useState<StandingsT | null>(null);
  const [p1, p2] = game.players;

  useEffect(() => {
    api.standings(game.id).then(setData);
  }, [game.id]);

  if (!data) return <Banner tone="info">加载中…</Banner>;

  const s1 = data.players[p1.id];
  const s2 = data.players[p2.id];
  const f1 = Number(s1.final_score);
  const f2 = Number(s2.final_score);
  const max = Math.max(Math.abs(f1), Math.abs(f2), 1);
  const isChamp = (id: string) => data.champion_ids.includes(id);

  return (
    <div className="space-y-3">
      <Card className="border-emerald-900/15">
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-slate-700">最终加权积分</h2>
          <span className="rounded-md bg-cup-deep px-2 py-1 text-xs font-semibold text-cup-gold">🏆 TABLE</span>
        </div>
        {[
          { p: p1, s: s1, f: f1 },
          { p: p2, s: s2, f: f2 },
        ].map(({ p, s, f }) => (
          <div key={p.id} className="mb-3">
            <div className="flex items-center justify-between text-sm">
              <span className="font-medium">
                {p.name} {isChamp(p.id) && <Pill tone="amber">领先</Pill>}
              </span>
              <span className="font-mono font-semibold">{s.final_score}</span>
            </div>
            <div className="mt-1 h-2 rounded-full bg-emerald-50">
              <div
                className="h-2 rounded-full bg-[linear-gradient(90deg,#0f766e,#f6c453)]"
                style={{ width: `${Math.max((Math.abs(f) / max) * 100, 2)}%` }}
              />
            </div>
          </div>
        ))}
        {data.blowout && (
          <Banner tone="info">
            当前分差比例 ≥ 25%，若维持到最终将触发「大胜」（追加失败者复盘 + 冠军夸夸）。
          </Banner>
        )}
      </Card>

      <Card className="border-emerald-900/15">
        <h2 className="mb-2 text-sm font-semibold text-slate-700">各轮净积分</h2>
        <table className="w-full text-sm">
          <thead>
            <tr className="text-xs text-emerald-700">
              <th className="text-left font-normal">轮次</th>
              <th className="text-left font-normal">权重</th>
              <th className="text-right font-normal">{p1.name}</th>
              <th className="text-right font-normal">{p2.name}</th>
            </tr>
          </thead>
          <tbody>
            {ROUNDS.map((r) => (
              <tr key={r} className="border-t border-emerald-100">
                <td className="py-1.5">{r}</td>
                <td className="text-slate-400">{WEIGHTS[r]}</td>
                <td className="text-right font-mono">{s1.round_nets[r]}</td>
                <td className="text-right font-mono">{s2.round_nets[r]}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <p className="mt-2 text-xs text-slate-400">
          未加权累计：{p1.name} {s1.unweighted_net} / {p2.name} {s2.unweighted_net}。
          精确比分命中：{p1.name} {s1.exact_hits} 次 / {p2.name} {s2.exact_hits} 次。
        </p>
      </Card>
    </div>
  );
}
