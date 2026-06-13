import { useEffect, useState } from "react";
import { api } from "../api";
import { useAppState } from "../store";
import type { Game, Match } from "../types";
import { Banner, Button, Card, Field, Input, Pill } from "../ui";

function OddsEditor({ match, recorder, onSaved }: { match: Match; recorder: string; onSaved: () => void }) {
  const [h, setH] = useState(match.odds?.home_odds ?? "");
  const [d, setD] = useState(match.odds?.draw_odds ?? "");
  const [a, setA] = useState(match.odds?.away_odds ?? "");
  const [source, setSource] = useState(match.odds?.source ?? "OddsPortal");
  const [adminPin, setAdminPin] = useState("");
  const [err, setErr] = useState<string | null>(null);
  const [ok, setOk] = useState(false);

  async function save(available: boolean) {
    setErr(null);
    setOk(false);
    if (!adminPin.trim()) {
      setErr("请填写管理 PIN");
      return;
    }
    try {
      await api.submitOdds(match.id, {
        recorded_by: recorder,
        home_odds: available ? h || null : null,
        draw_odds: available ? d || null : null,
        away_odds: available ? a || null : null,
        available,
        source: available ? source : "无盘",
        admin_pin: adminPin.trim(),
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
      <Field label="管理 PIN">
        <Input
          type="password"
          value={adminPin}
          onChange={(e) => setAdminPin(e.target.value)}
          placeholder="修改赔率需要 PIN"
        />
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
        每场比赛在开赛前 1 小时锁定（北京时间），锁定后赔率与预测不可改。赛果由系统自动获取并结算。
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
          {m.status === "已结算" && m.home_goals !== null && (
            <div className="mt-2 text-sm text-slate-500">
              赛果：{m.home_team} {m.home_goals} : {m.away_goals} {m.away_team}（自动结算）
            </div>
          )}
        </Card>
      ))}
    </div>
  );
}
