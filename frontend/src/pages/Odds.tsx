import { useEffect, useState } from "react";
import { api } from "../api";
import { useAppState } from "../store";
import type { Game, Match, WDL } from "../types";
import { Banner, Button, Card, Field, Input, Pill } from "../ui";

function OddsEditor({ match, recorder, onSaved }: { match: Match; recorder: string; onSaved: () => void }) {
  const [h, setH] = useState(match.odds?.home_odds ?? "");
  const [d, setD] = useState(match.odds?.draw_odds ?? "");
  const [a, setA] = useState(match.odds?.away_odds ?? "");
  const [source, setSource] = useState(match.odds?.source ?? "OddsPortal");
  const [err, setErr] = useState<string | null>(null);
  const [ok, setOk] = useState(false);

  async function save(available: boolean) {
    setErr(null);
    setOk(false);
    try {
      await api.submitOdds(match.id, {
        recorded_by: recorder,
        home_odds: available ? h || null : null,
        draw_odds: available ? d || null : null,
        away_odds: available ? a || null : null,
        available,
        source: available ? source : "无盘",
      });
      setOk(true);
      onSaved();
    } catch (e) {
      setErr(String(e));
    }
  }

  if (match.locked) {
    return (
      <div className="mt-2 text-sm text-slate-500">
        已锁定，赔率不可改：
        {match.odds?.available
          ? ` ${match.odds.home_odds} / ${match.odds.draw_odds} / ${match.odds.away_odds}`
          : " 赔率缺失"}
      </div>
    );
  }

  return (
    <div className="mt-3 space-y-2 rounded-xl bg-slate-50 p-3">
      <div className="grid grid-cols-3 gap-2">
        <Field label="主胜">
          <Input type="number" step="0.01" min="1" value={h} onChange={(e) => setH(e.target.value)} />
        </Field>
        <Field label="平">
          <Input type="number" step="0.01" min="1" value={d} onChange={(e) => setD(e.target.value)} />
        </Field>
        <Field label="客胜">
          <Input type="number" step="0.01" min="1" value={a} onChange={(e) => setA(e.target.value)} />
        </Field>
      </div>
      <Field label="来源">
        <Input value={source} onChange={(e) => setSource(e.target.value)} />
      </Field>
      {err && <Banner tone="error">{err}</Banner>}
      {ok && <Banner tone="success">已保存赔率快照</Banner>}
      <div className="flex gap-2">
        <Button onClick={() => save(true)} className="flex-1">
          保存赔率
        </Button>
        <Button variant="ghost" onClick={() => save(false)}>
          标记赔率缺失
        </Button>
      </div>
    </div>
  );
}

function ResultEditor({ match, actor, onSaved }: { match: Match; actor: string; onSaved: () => void }) {
  const [open, setOpen] = useState(false);
  const [h, setH] = useState(match.home_goals?.toString() ?? "");
  const [a, setA] = useState(match.away_goals?.toString() ?? "");
  const [adv, setAdv] = useState<WDL>(match.advanced_team ?? "主胜");
  const [err, setErr] = useState<string | null>(null);
  const isKnockout = match.stage !== "小组赛";

  async function save() {
    setErr(null);
    if (h === "" || a === "") {
      setErr("请填写双方进球数");
      return;
    }
    try {
      await api.submitResult(match.id, {
        home_goals: Number(h),
        away_goals: Number(a),
        advanced_team: isKnockout ? adv : null,
        actor,
      });
      setOpen(false);
      onSaved();
    } catch (e) {
      setErr(String(e));
    }
  }

  if (!open)
    return (
      <Button variant="soft" className="mt-2 w-full" onClick={() => setOpen(true)}>
        {match.home_goals !== null ? "修改赛果" : "录入赛果并结算"}
      </Button>
    );

  return (
    <div className="mt-2 space-y-2 rounded-xl bg-slate-50 p-3">
      <div className="flex items-end gap-2">
        <Field label={`${match.home_team}（加时后，不含点球）`}>
          <Input type="number" min={0} value={h} onChange={(e) => setH(e.target.value)} />
        </Field>
        <span className="pb-2">:</span>
        <Field label={`${match.away_team}`}>
          <Input type="number" min={0} value={a} onChange={(e) => setA(e.target.value)} />
        </Field>
      </div>
      {isKnockout && (
        <Field label="最终晋级方（含点球）">
          <div className="flex gap-2">
            {(["主胜", "客胜"] as WDL[]).map((w) => (
              <button
                key={w}
                onClick={() => setAdv(w)}
                className={`rounded-lg px-3 py-1 text-sm ${
                  adv === w ? "bg-brand text-white" : "bg-white border border-slate-200 text-slate-600"
                }`}
              >
                {w === "主胜" ? match.home_team : match.away_team}
              </button>
            ))}
          </div>
        </Field>
      )}
      {err && <Banner tone="error">{err}</Banner>}
      <div className="flex gap-2">
        <Button onClick={save} className="flex-1">
          保存并结算
        </Button>
        <Button variant="ghost" onClick={() => setOpen(false)}>
          取消
        </Button>
      </div>
    </div>
  );
}

export default function Odds({ game }: { game: Game }) {
  const { activePlayerId } = useAppState();
  const [matches, setMatches] = useState<Match[]>([]);
  const recorder = game.players.find((p) => p.id === activePlayerId)?.name ?? "admin";

  function reload() {
    api.listMatches(game.id).then(setMatches);
  }
  useEffect(reload, [game.id]);

  return (
    <div className="space-y-3">
      <Banner tone="info">
        每场比赛在开赛前 1 小时锁定（北京时间），锁定后赔率与预测不可改。两名玩家均可录入赔率与赛果，操作记入留痕。
      </Banner>
      {matches.map((m) => (
        <Card key={m.id}>
          <div className="flex items-center justify-between">
            <div className="font-semibold">
              {m.home_team} <span className="text-slate-300">vs</span> {m.away_team}
            </div>
            <Pill tone={m.status === "已结算" ? "green" : m.locked ? "amber" : "slate"}>
              {m.status}
            </Pill>
          </div>
          <div className="text-xs text-slate-400">
            {m.stage} · 锁定 {new Date(m.lock_time_beijing).toLocaleString("zh-CN")}
          </div>
          <OddsEditor match={m} recorder={recorder} onSaved={reload} />
          <ResultEditor match={m} actor={recorder} onSaved={reload} />
        </Card>
      ))}
    </div>
  );
}
