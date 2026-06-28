import { useEffect, useState } from "react";
import { api } from "../api";
import type { Game, Match } from "../types";
import { Banner, Card, Pill } from "../ui";
import { StageBadge, TeamName } from "../worldCup";
import { teamWithFlag } from "../worldCupData";

const BREAKDOWN_LABELS: Record<string, string> = {
  reason: "说明",
  mode: "模式",
  stake: "Double 本金",
  odds: "使用赔率",
  odds_source: "赔率来源",
  wdl_correct: "胜平负",
  wdl_points: "胜平负得分",
  base: "Double 基础分",
  gd_bonus: "净胜球加分",
  score_bonus: "精确比分加分",
  total: "合计",
};

const BREAKDOWN_ORDER = [
  "reason",
  "mode",
  "odds",
  "odds_source",
  "stake",
  "wdl_correct",
  "wdl_points",
  "base",
  "gd_bonus",
  "score_bonus",
  "total",
];

function formatScore(value: string) {
  const n = Number(value);
  if (!Number.isFinite(n)) return value;
  return n.toLocaleString("zh-CN", { maximumFractionDigits: 2 });
}

function formatBreakdownValue(key: string, value: unknown) {
  if (typeof value === "boolean") return value ? "命中" : "未命中";
  if (value === null || value === undefined || value === "") return "无";
  if (key === "mode" && value === "Double") return "Double";
  if (key === "mode" && value === "普通") return "普通";
  return String(value);
}

function breakdownEntries(breakdown: Record<string, unknown>) {
  const keys = [
    ...BREAKDOWN_ORDER.filter((key) => key in breakdown),
    ...Object.keys(breakdown).filter((key) => !BREAKDOWN_ORDER.includes(key)),
  ];
  return keys.map((key) => ({
    key,
    label: BREAKDOWN_LABELS[key] ?? key,
    value: formatBreakdownValue(key, breakdown[key]),
  }));
}

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
          className="flex-1 rounded-lg bg-emerald-50 py-2 text-center text-sm font-medium text-brand"
        >
          导出 JSON
        </a>
        <a
          href={api.exportCsvUrl(game.id)}
          className="flex-1 rounded-lg bg-emerald-50 py-2 text-center text-sm font-medium text-brand"
        >
          导出 CSV
        </a>
      </div>

      {settled.length === 0 && <Banner tone="info">还没有已结算的比赛。</Banner>}

      {settled.map((m) => (
        <Card key={m.id} className="border-emerald-900/15">
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <div className="mb-2 flex items-center gap-2">
                <StageBadge stage={m.stage} />
                <span className="text-xs text-slate-400">锁定 {new Date(m.lock_time_beijing).toLocaleString("zh-CN")}</span>
              </div>
              <div className="grid grid-cols-[1fr_auto_1fr] items-center gap-2 rounded-lg bg-emerald-950 px-3 py-2 text-white">
                <span className="min-w-0 text-sm font-semibold"><TeamName team={m.home_team} /></span>
                <span className="font-mono text-xl font-bold text-cup-gold">{m.home_goals}:{m.away_goals}</span>
                <span className="min-w-0 text-sm font-semibold"><TeamName team={m.away_team} /></span>
              </div>
            </div>
            <Pill tone="green">已结算</Pill>
          </div>
          <div className="text-xs text-slate-400">
            {m.odds?.available &&
              `赔率快照 ${m.odds.home_odds}/${m.odds.draw_odds}/${m.odds.away_odds}`}
            {m.advanced_team && ` · 晋级 ${teamWithFlag(m.advanced_team === "主胜" ? m.home_team : m.away_team)}`}
          </div>

          <div className="mt-2 space-y-2">
            {m.scores?.map((s) => (
              <div key={s.player_id} className="rounded-lg bg-emerald-50/70 p-2 ring-1 ring-emerald-100">
                <div className="flex items-center justify-between text-sm">
                  <span className="font-medium">
                    {nameOf(s.player_id)}{" "}
                    {s.mode === "Double" && <Pill tone="rose">Double</Pill>}
                    {s.manual_override && <Pill tone="amber">人工改分</Pill>}
                  </span>
                  <span className="font-mono font-semibold">{formatScore(s.score)}</span>
                </div>
                {s.breakdown && (
                  <div className="mt-2 flex flex-wrap gap-1.5">
                    {breakdownEntries(s.breakdown).map((item) => (
                      <span
                        key={item.key}
                        className="rounded-lg bg-white px-2 py-1 text-[11px] text-slate-500 ring-1 ring-emerald-100"
                      >
                        <span className="text-slate-400">{item.label}：</span>
                        <span className="font-medium text-slate-600">{item.value}</span>
                      </span>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </Card>
      ))}
    </div>
  );
}
