import { useEffect, useState } from "react";
import { api } from "../api";
import { useAppState } from "../store";
import type { Game, Match, MatchDay as MatchDayT, Prediction, WDL } from "../types";
import { Banner, Button, Card, Field, Input, Pill } from "../ui";
type MatchFilter = "all" | "today" | "pending" | "mine_unpredicted" | "settled";

const FILTERS: { value: MatchFilter; label: string }[] = [
  { value: "all", label: "全部" },
  { value: "today", label: "今日" },
  { value: "pending", label: "待预测" },
  { value: "mine_unpredicted", label: "我的未预测" },
  { value: "settled", label: "已结算" },
];

function fmtTime(iso: string) {
  return new Date(iso).toLocaleString("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function todayBeijing() {
  const parts = new Intl.DateTimeFormat("en-US", {
    timeZone: "Asia/Shanghai",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).formatToParts(new Date());
  const value = (type: string) => parts.find((p) => p.type === type)?.value ?? "";
  return `${value("year")}-${value("month")}-${value("day")}`;
}

function wdlFromScore(home: number, away: number): WDL {
  if (home > away) return "主胜";
  if (home < away) return "客胜";
  return "平";
}

function predictionWdl(pred: Prediction): WDL {
  if (pred.has_score && pred.pred_home !== null && pred.pred_away !== null) {
    return wdlFromScore(pred.pred_home, pred.pred_away);
  }
  return pred.wdl;
}

function PredictionForm({
  match,
  playerId,
  onSaved,
}: {
  match: Match;
  playerId: string;
  onSaved: () => void;
}) {
  const existing = match.predictions.find((p) => p.player_id === playerId);
  const [home, setHome] = useState<string>(existing?.pred_home?.toString() ?? "");
  const [away, setAway] = useState<string>(existing?.pred_away?.toString() ?? "");
  const [useDouble, setUseDouble] = useState(existing?.use_double ?? false);
  const [playerPin, setPlayerPin] = useState("");
  const [err, setErr] = useState<string | null>(null);
  const [ok, setOk] = useState(false);

  const oddsAvailable = !!match.odds?.available;
  const doubleAllowed = oddsAvailable && !match.is_final;
  const sp = match.stage_points;

  async function save() {
    setErr(null);
    setOk(false);
    if (playerPin.trim().length < 4) {
      setErr("请填写当前玩家 PIN");
      return;
    }
    if (home === "" || away === "") {
      setErr("请填写预测比分");
      return;
    }
    const predHome = Number(home);
    const predAway = Number(away);
    if (!Number.isInteger(predHome) || !Number.isInteger(predAway) || predHome < 0 || predAway < 0) {
      setErr("比分必须是非负整数");
      return;
    }
    const body: Parameters<typeof api.submitPrediction>[1] = {
      player_id: playerId,
      player_pin: playerPin.trim(),
      wdl: wdlFromScore(predHome, predAway),
      has_score: true,
      pred_home: predHome,
      pred_away: predAway,
      use_double: useDouble,
    };
    try {
      await api.submitPrediction(match.id, body);
      setOk(true);
      onSaved();
    } catch (e) {
      setErr(String(e));
    }
  }

  return (
    <div className="mt-3 space-y-3 rounded-xl bg-slate-50 p-3">
      <div className="flex items-end gap-2">
        <Field label={`${match.home_team} 进球`}>
          <Input type="number" min={0} step={1} value={home} onChange={(e) => setHome(e.target.value)} />
        </Field>
        <span className="pb-2 text-slate-400">:</span>
        <Field label={`${match.away_team} 进球`}>
          <Input type="number" min={0} step={1} value={away} onChange={(e) => setAway(e.target.value)} />
        </Field>
      </div>

      {home !== "" && away !== "" && Number.isInteger(Number(home)) && Number.isInteger(Number(away)) && (
        <div className="text-xs text-slate-500">
          系统将自动判定为：{wdlFromScore(Number(home), Number(away))}，净胜球 {Number(home) - Number(away)}。
        </div>
      )}

      <label className="flex items-center gap-2 text-sm">
        <input
          type="checkbox"
          checked={useDouble}
          disabled={!doubleAllowed}
          onChange={(e) => setUseDouble(e.target.checked)}
        />
        <span className={doubleAllowed ? "text-slate-700" : "text-slate-400"}>
          使用 Double（本金 {sp.w}）
        </span>
        {match.is_final && <Pill tone="amber">决赛禁用</Pill>}
        {!match.is_final && !oddsAvailable && <Pill tone="amber">赔率缺失不可用</Pill>}
      </label>

      <div className="text-xs text-slate-500">
        基础分：胜平负 {sp.w} / 净胜球 {sp.gd} / 精确比分 {sp.sc}（满分 {sp.full}）。
        {useDouble && oddsAvailable && (
          <>
            {" "}
            Double 会跟随比分自动判定的胜平负；押中 = 本金 {sp.w} ×（赔率−1）+命中加分，押错 = −{sp.w}。
          </>
        )}
      </div>

      <Field label="当前玩家 PIN">
        <Input
          type="password"
          value={playerPin}
          onChange={(e) => setPlayerPin(e.target.value)}
          placeholder="保存预测需要 PIN"
        />
      </Field>

      {err && <Banner tone="error">{err}</Banner>}
      {ok && <Banner tone="success">已保存</Banner>}
      <Button onClick={save} className="w-full">
        保存预测
      </Button>
    </div>
  );
}

function PredictionView({ pred, name }: { pred: Prediction; name: string }) {
  const effectiveWdl = predictionWdl(pred);
  let detail = effectiveWdl;
  if (pred.has_score) detail += ` · 比分 ${pred.pred_home}:${pred.pred_away}`;
  else if (pred.has_gd) detail += ` · 净胜球 ${pred.sgd}`;
  const boundOdds =
    effectiveWdl === "主胜" ? pred.bound_home_odds : effectiveWdl === "平" ? pred.bound_draw_odds : pred.bound_away_odds;
  return (
    <div className="flex items-center justify-between text-sm">
      <span className="text-slate-500">{name}</span>
      <span className="text-slate-700">
        {detail} {pred.use_double && <Pill tone="rose">Double{boundOdds ? ` @${boundOdds}` : ""}</Pill>}
      </span>
    </div>
  );
}

function EditablePrediction({
  match,
  playerId,
  playerName,
  onSaved,
}: {
  match: Match;
  playerId: string;
  playerName: string;
  onSaved: () => void;
}) {
  const existing = match.predictions.find((p) => p.player_id === playerId);
  const [editing, setEditing] = useState(!existing);

  if (!editing && existing) {
    return (
      <div className="mt-3 space-y-2 rounded-xl bg-slate-50 p-3">
        <PredictionView pred={existing} name={playerName} />
        <Button variant="soft" className="w-full" onClick={() => setEditing(true)}>
          修改预测
        </Button>
      </div>
    );
  }

  return (
    <PredictionForm
      match={match}
      playerId={playerId}
      onSaved={() => {
        setEditing(false);
        onSaved();
      }}
    />
  );
}

export default function MatchDay({ game }: { game: Game }) {
  const { activePlayerId } = useAppState();
  const [days, setDays] = useState<MatchDayT[]>([]);
  const [selected, setSelected] = useState<string | "all">("all");
  const [filter, setFilter] = useState<MatchFilter>("all");
  const [matches, setMatches] = useState<Match[]>([]);

  function reload() {
    api.listMatchDays(game.id).then(setDays);
    api.listMatches(game.id, selected === "all" ? undefined : selected, activePlayerId).then(setMatches);
  }

  useEffect(reload, [game.id, selected, activePlayerId]);

  const nameOf = (id: string) => game.players.find((p) => p.id === id)?.name ?? id;
  const beijingToday = todayBeijing();
  const filteredMatches = matches.filter((m) => {
    if (filter === "today") return m.match_day === beijingToday;
    if (filter === "pending") return m.status === "待预测" && !m.locked;
    if (filter === "mine_unpredicted") {
      return (
        !!activePlayerId &&
        !m.locked &&
        m.status === "待预测" &&
        !m.predictions.some((p) => p.player_id === activePlayerId)
      );
    }
    if (filter === "settled") return m.status === "已结算" || m.home_goals !== null;
    return true;
  });

  function selectFilter(next: MatchFilter) {
    setFilter(next);
    if (next === "today") {
      setSelected("all");
    }
  }

  function selectDay(next: string | "all") {
    setSelected(next);
    if (filter === "today") {
      setFilter("all");
    }
  }

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap gap-1">
        <button
          onClick={() => selectDay("all")}
          className={`rounded-lg px-3 py-1 text-xs ${
            selected === "all" ? "bg-slate-800 text-white" : "bg-slate-100 text-slate-600"
          }`}
        >
          全部
        </button>
        {days.map((d) => (
          <button
            key={d.match_day}
            onClick={() => selectDay(d.match_day)}
            className={`rounded-lg px-3 py-1 text-xs ${
              selected === d.match_day ? "bg-slate-800 text-white" : "bg-slate-100 text-slate-600"
            }`}
          >
            {d.match_day.slice(5)} {d.locked ? "🔒" : ""}
          </button>
        ))}
      </div>

      <div className="flex flex-wrap gap-1 rounded-xl bg-white p-2 shadow-sm ring-1 ring-slate-100">
        {FILTERS.map((item) => (
          <button
            key={item.value}
            onClick={() => selectFilter(item.value)}
            className={`rounded-lg px-3 py-1 text-xs font-medium ${
              filter === item.value ? "bg-brand text-white" : "bg-slate-100 text-slate-600"
            }`}
          >
            {item.label}
          </button>
        ))}
      </div>

      {filter === "mine_unpredicted" && !activePlayerId && (
        <Banner tone="info">请先在顶部选择当前玩家，再查看我的未预测。</Banner>
      )}

      {filteredMatches.length === 0 && (
        <Banner tone="info">当前筛选下暂无比赛。</Banner>
      )}

      {filteredMatches.map((m) => (
        <Card key={m.id}>
          <div className="flex items-start justify-between">
            <div>
              <div className="font-semibold">
                {m.home_team} <span className="text-slate-300">vs</span> {m.away_team}
              </div>
              <div className="mt-0.5 text-xs text-slate-400">
                {m.stage} · {m.round} · 开赛 {fmtTime(m.kickoff_beijing)}
              </div>
              <div className="text-xs text-slate-400">锁定 {fmtTime(m.lock_time_beijing)}</div>
            </div>
            <div className="flex flex-col items-end gap-1">
              <Pill tone={m.status === "已结算" ? "green" : m.locked ? "amber" : "slate"}>
                {m.status}
              </Pill>
              {m.odds?.available && (
                <span className="text-[11px] text-slate-400">
                  赔率 {m.odds.home_odds}/{m.odds.draw_odds}/{m.odds.away_odds}
                </span>
              )}
            </div>
          </div>

          {m.home_goals !== null && (
            <div className="mt-2 flex items-center justify-center gap-3 rounded-lg bg-green-50 py-2 text-center">
              <span className="font-semibold text-green-800">{m.home_team}</span>
              <span className="text-xl font-bold text-green-700">{m.home_goals} : {m.away_goals}</span>
              <span className="font-semibold text-green-800">{m.away_team}</span>
              {m.advanced_team && (
                <Pill tone="green">晋级 {m.advanced_team === "主胜" ? m.home_team : m.away_team}</Pill>
              )}
            </div>
          )}

          {!m.locked && activePlayerId ? (
            <EditablePrediction match={m} playerId={activePlayerId} playerName={nameOf(activePlayerId)} onSaved={reload} />
          ) : null}

          <div className="mt-3 space-y-1 border-t border-slate-100 pt-2">
            {m.predictions.length === 0 && (
              <p className="text-xs text-slate-400">无预测记录</p>
            )}
            {m.predictions
              .filter((p) => m.locked || p.player_id === activePlayerId)
              .map((p) => (
                <PredictionView key={p.player_id} pred={p} name={nameOf(p.player_id)} />
              ))}
          </div>
        </Card>
      ))}
    </div>
  );
}
