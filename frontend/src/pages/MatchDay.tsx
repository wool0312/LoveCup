import { useEffect, useState } from "react";
import { api } from "../api";
import { useAppState } from "../store";
import type { Game, Match, MatchDay as MatchDayT, Prediction, WDL } from "../types";
import { Banner, Button, Card, Field, Input, Pill } from "../ui";

const STAGES = ["小组赛", "32强", "16强", "8强", "半决赛", "三四名", "决赛"];
const WDLS: WDL[] = ["主胜", "平", "客胜"];
type Mode = "wdl" | "gd" | "score";

function fmtTime(iso: string) {
  return new Date(iso).toLocaleString("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
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
  const initMode: Mode = existing?.has_score ? "score" : existing?.has_gd ? "gd" : "wdl";
  const [wdl, setWdl] = useState<WDL>(existing?.wdl ?? "主胜");
  const [mode, setMode] = useState<Mode>(initMode);
  const [sgd, setSgd] = useState<string>(existing?.sgd?.toString() ?? "0");
  const [home, setHome] = useState<string>(existing?.pred_home?.toString() ?? "");
  const [away, setAway] = useState<string>(existing?.pred_away?.toString() ?? "");
  const [useDouble, setUseDouble] = useState(existing?.use_double ?? false);
  const [err, setErr] = useState<string | null>(null);
  const [ok, setOk] = useState(false);

  const oddsAvailable = !!match.odds?.available;
  const doubleAllowed = oddsAvailable && !match.is_final;
  const sp = match.stage_points;

  async function save() {
    setErr(null);
    setOk(false);
    const body: Parameters<typeof api.submitPrediction>[1] = {
      player_id: playerId,
      wdl,
      use_double: useDouble,
    };
    if (mode === "gd") {
      body.has_gd = true;
      body.sgd = Number(sgd);
    } else if (mode === "score") {
      if (home === "" || away === "") {
        setErr("精确比分需要填写双方进球数");
        return;
      }
      body.has_score = true;
      body.pred_home = Number(home);
      body.pred_away = Number(away);
    }
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
      <div className="flex flex-wrap gap-1">
        {WDLS.map((w) => (
          <button
            key={w}
            onClick={() => setWdl(w)}
            className={`rounded-lg px-3 py-1 text-sm ${
              wdl === w ? "bg-brand text-white" : "bg-white text-slate-600 border border-slate-200"
            }`}
          >
            {w}
          </button>
        ))}
      </div>

      <div className="flex flex-wrap gap-1 text-xs">
        {([
          ["wdl", "只猜胜平负"],
          ["gd", "+净胜球"],
          ["score", "精确比分"],
        ] as [Mode, string][]).map(([m, label]) => (
          <button
            key={m}
            onClick={() => setMode(m)}
            className={`rounded-lg px-2 py-1 ${
              mode === m ? "bg-slate-800 text-white" : "bg-white text-slate-500 border border-slate-200"
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {mode === "gd" && (
        <Field label="净胜球（主−客，可负）">
          <Input type="number" value={sgd} onChange={(e) => setSgd(e.target.value)} />
        </Field>
      )}
      {mode === "score" && (
        <div className="flex items-end gap-2">
          <Field label={`${match.home_team} 进球`}>
            <Input type="number" min={0} value={home} onChange={(e) => setHome(e.target.value)} />
          </Field>
          <span className="pb-2 text-slate-400">:</span>
          <Field label={`${match.away_team} 进球`}>
            <Input type="number" min={0} value={away} onChange={(e) => setAway(e.target.value)} />
          </Field>
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
            Double 押中 = 本金 {sp.w} ×（赔率−1）+命中加分；押错 = −{sp.w}。
          </>
        )}
      </div>

      {err && <Banner tone="error">{err}</Banner>}
      {ok && <Banner tone="success">已保存</Banner>}
      <Button onClick={save} className="w-full">
        保存预测
      </Button>
    </div>
  );
}

function PredictionView({ pred, name }: { pred: Prediction; name: string }) {
  let detail = pred.wdl;
  if (pred.has_score) detail += ` · 比分 ${pred.pred_home}:${pred.pred_away}`;
  else if (pred.has_gd) detail += ` · 净胜球 ${pred.sgd}`;
  return (
    <div className="flex items-center justify-between text-sm">
      <span className="text-slate-500">{name}</span>
      <span className="text-slate-700">
        {detail} {pred.use_double && <Pill tone="rose">Double</Pill>}
      </span>
    </div>
  );
}

function AddMatch({ game, onAdded }: { game: Game; onAdded: () => void }) {
  const [open, setOpen] = useState(false);
  const [stage, setStage] = useState(STAGES[0]);
  const [home, setHome] = useState("");
  const [away, setAway] = useState("");
  const [kickoff, setKickoff] = useState("");
  const [err, setErr] = useState<string | null>(null);

  async function add() {
    setErr(null);
    if (!home.trim() || !away.trim() || !kickoff) {
      setErr("请填写主队、客队和开赛时间");
      return;
    }
    try {
      await api.createMatch(game.id, {
        stage,
        home_team: home.trim(),
        away_team: away.trim(),
        kickoff_at: `${kickoff}:00+08:00`, // 输入按北京时间处理
      });
      setHome("");
      setAway("");
      setKickoff("");
      setOpen(false);
      onAdded();
    } catch (e) {
      setErr(String(e));
    }
  }

  if (!open)
    return (
      <Button variant="soft" className="w-full" onClick={() => setOpen(true)}>
        + 新增比赛
      </Button>
    );

  return (
    <Card className="space-y-2">
      <div className="flex flex-wrap gap-1">
        {STAGES.map((s) => (
          <button
            key={s}
            onClick={() => setStage(s)}
            className={`rounded-lg px-2 py-1 text-xs ${
              stage === s ? "bg-brand text-white" : "bg-slate-100 text-slate-600"
            }`}
          >
            {s}
          </button>
        ))}
      </div>
      <div className="flex gap-2">
        <Input placeholder="主队" value={home} onChange={(e) => setHome(e.target.value)} />
        <Input placeholder="客队" value={away} onChange={(e) => setAway(e.target.value)} />
      </div>
      <Field label="开赛时间（北京时间）">
        <Input type="datetime-local" value={kickoff} onChange={(e) => setKickoff(e.target.value)} />
      </Field>
      {err && <Banner tone="error">{err}</Banner>}
      <div className="flex gap-2">
        <Button onClick={add} className="flex-1">
          添加
        </Button>
        <Button variant="ghost" onClick={() => setOpen(false)}>
          取消
        </Button>
      </div>
    </Card>
  );
}

export default function MatchDay({ game }: { game: Game }) {
  const { activePlayerId } = useAppState();
  const [days, setDays] = useState<MatchDayT[]>([]);
  const [selected, setSelected] = useState<string | "all">("all");
  const [matches, setMatches] = useState<Match[]>([]);

  function reload() {
    api.listMatchDays(game.id).then(setDays);
    api.listMatches(game.id, selected === "all" ? undefined : selected).then(setMatches);
  }

  useEffect(reload, [game.id, selected]);

  const nameOf = (id: string) => game.players.find((p) => p.id === id)?.name ?? id;

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap gap-1">
        <button
          onClick={() => setSelected("all")}
          className={`rounded-lg px-3 py-1 text-xs ${
            selected === "all" ? "bg-slate-800 text-white" : "bg-slate-100 text-slate-600"
          }`}
        >
          全部
        </button>
        {days.map((d) => (
          <button
            key={d.match_day}
            onClick={() => setSelected(d.match_day)}
            className={`rounded-lg px-3 py-1 text-xs ${
              selected === d.match_day ? "bg-slate-800 text-white" : "bg-slate-100 text-slate-600"
            }`}
          >
            {d.match_day.slice(5)} {d.locked ? "🔒" : ""}
          </button>
        ))}
      </div>

      <AddMatch game={game} onAdded={reload} />

      {matches.length === 0 && (
        <Banner tone="info">该比赛日还没有比赛，点上方「新增比赛」添加。</Banner>
      )}

      {matches.map((m) => (
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
            <div className="mt-2 text-sm text-slate-600">
              赛果 {m.home_goals}:{m.away_goals}
              {m.advanced_team && ` · 晋级 ${m.advanced_team}`}
            </div>
          )}

          {!m.locked && activePlayerId ? (
            <PredictionForm match={m} playerId={activePlayerId} onSaved={reload} />
          ) : (
            <div className="mt-3 space-y-1 border-t border-slate-100 pt-2">
              {m.predictions.length === 0 && (
                <p className="text-xs text-slate-400">无预测记录</p>
              )}
              {m.predictions.map((p) => (
                <PredictionView key={p.player_id} pred={p} name={nameOf(p.player_id)} />
              ))}
            </div>
          )}
        </Card>
      ))}
    </div>
  );
}
