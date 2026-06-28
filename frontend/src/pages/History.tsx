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

function fmtHistoryTime(iso: string) {
  return new Date(iso).toLocaleString("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export default function History({ game }: { game: Game }) {
  const [matches, setMatches] = useState<Match[]>([]);
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set());
  const nameOf = (id: string) => game.players.find((p) => p.id === id)?.name ?? id;

  useEffect(() => {
    api.history(game.id).then((items) => {
      const settledItems = items
        .filter((m) => m.status === "已结算")
        .sort((a, b) => new Date(b.kickoff_beijing).getTime() - new Date(a.kickoff_beijing).getTime());
      setMatches(items);
      setExpandedIds(settledItems[0] ? new Set([settledItems[0].id]) : new Set());
    });
  }, [game.id]);

  const settled = matches
    .filter((m) => m.status === "已结算")
    .sort((a, b) => new Date(b.kickoff_beijing).getTime() - new Date(a.kickoff_beijing).getTime());

  function toggleMatch(matchId: string) {
    setExpandedIds((current) => {
      const next = new Set(current);
      if (next.has(matchId)) next.delete(matchId);
      else next.add(matchId);
      return next;
    });
  }

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

      <div className="relative space-y-3 pl-5 before:absolute before:bottom-2 before:left-2 before:top-2 before:w-px before:bg-emerald-200">
        {settled.map((m, index) => {
          const expanded = expandedIds.has(m.id);
          const winner =
            m.advanced_team === "主胜"
              ? m.home_team
              : m.advanced_team === "客胜"
                ? m.away_team
                : null;

          return (
            <div
              key={m.id}
              className="match-card-enter relative"
              style={{ animationDelay: `${Math.min(index, 8) * 45}ms` }}
            >
              <span className="absolute -left-[1.05rem] top-5 h-3 w-3 rounded-full border-2 border-white bg-cup-gold shadow-sm shadow-emerald-900/20" />
              <Card className="overflow-hidden border-emerald-900/15 p-0">
                <button
                  type="button"
                  onClick={() => toggleMatch(m.id)}
                  className="block w-full px-4 py-3 text-left hover:bg-emerald-50/60"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <div className="mb-2 flex flex-wrap items-center gap-2">
                        <StageBadge stage={m.stage} />
                        <span className="text-xs text-slate-400">{fmtHistoryTime(m.kickoff_beijing)}</span>
                        {winner && <span className="text-xs text-emerald-700">晋级 {teamWithFlag(winner)}</span>}
                      </div>
                      <div className="grid grid-cols-[1fr_auto_1fr] items-center gap-2 rounded-lg bg-emerald-950 px-3 py-2 text-center text-white">
                        <span className="min-w-0 text-sm font-semibold"><TeamName team={m.home_team} /></span>
                        <span className="font-mono text-xl font-bold text-cup-gold">{m.home_goals}:{m.away_goals}</span>
                        <span className="min-w-0 text-sm font-semibold"><TeamName team={m.away_team} /></span>
                      </div>
                    </div>
                    <span className="rounded-full bg-emerald-50 px-2 py-1 text-xs font-medium text-emerald-800">
                      {expanded ? "收起" : "展开"}
                    </span>
                  </div>
                </button>

                {expanded && (
                  <div className="space-y-3 border-t border-emerald-100 px-4 py-3">
                    <div className="text-xs text-slate-400">
                      锁定 {new Date(m.lock_time_beijing).toLocaleString("zh-CN")}
                      {m.odds?.available &&
                        ` · 赔率快照 ${m.odds.home_odds}/${m.odds.draw_odds}/${m.odds.away_odds}`}
                    </div>

                    <div className="space-y-2">
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
                  </div>
                )}
              </Card>
            </div>
          );
        })}
      </div>
    </div>
  );
}
