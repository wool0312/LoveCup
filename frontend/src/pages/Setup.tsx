import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api";
import { setActivePlayer, setGameId, useAppState } from "../store";
import { Banner, Button, Card, Field, Input } from "../ui";

export default function Setup() {
  const { gameId } = useAppState();
  const nav = useNavigate();
  const [customId, setCustomId] = useState("");
  const [p1, setP1] = useState("");
  const [p2, setP2] = useState("");
  const [budget, setBudget] = useState("1000");
  const [err, setErr] = useState<string | null>(null);
  const [loadId, setLoadId] = useState("");

  async function create() {
    setErr(null);
    if (!p1.trim() || !p2.trim()) {
      setErr("两名玩家昵称都必须填写");
      return;
    }
    if (Number(budget) < 0) {
      setErr("预算必须为非负数");
      return;
    }
    try {
      const game = await api.createGame({
        custom_id: customId.trim() || undefined,
        player1_name: p1.trim(),
        player2_name: p2.trim(),
        japan_budget_cny: budget,
      });
      setGameId(game.id);
      setActivePlayer(game.players[0].id);
      nav("/matchday");
    } catch (e) {
      setErr(String(e));
    }
  }

  async function load() {
    setErr(null);
    try {
      const g = await api.getGame(loadId.trim());
      setGameId(g.id);
      setActivePlayer(g.players[0].id);
      nav("/matchday");
    } catch {
      setErr("找不到该对局 ID");
    }
  }

  return (
    <div className="mx-auto flex min-h-full max-w-md flex-col justify-center gap-4 p-6">
      <div className="text-center">
        <h1 className="text-2xl font-bold text-brand">Love Cup 2026</h1>
        <p className="mt-1 text-sm text-slate-500">情侣世界杯竞猜积分游戏 · 规则 v0.5</p>
      </div>

      <Card className="space-y-3">
        <h2 className="text-sm font-semibold text-slate-700">开局设置</h2>
        <Field label="对局 ID（可选，留空自动生成）">
          <Input value={customId} onChange={(e) => setCustomId(e.target.value)} placeholder="例如 love2026" />
        </Field>
        <Field label="玩家 1 昵称">
          <Input value={p1} onChange={(e) => setP1(e.target.value)} placeholder="例如 wool" />
        </Field>
        <Field label="玩家 2 昵称">
          <Input value={p2} onChange={(e) => setP2(e.target.value)} placeholder="例如 mei" />
        </Field>
        <Field label="日本礼物预算上限（元）">
          <Input
            type="number"
            value={budget}
            onChange={(e) => setBudget(e.target.value)}
            min={0}
          />
        </Field>
        <div className="rounded-xl bg-slate-50 p-3 text-xs text-slate-500">
          规则版本 <b>v0.5</b> 一经确认锁定，不可中途修改。轮次权重 7 / 15 / 16 / 18 / 20 / 24（%）。
        </div>
        {err && <Banner tone="error">{err}</Banner>}
        <Button onClick={create} className="w-full">
          创建对局
        </Button>
      </Card>

      <Card className="space-y-2">
        <h2 className="text-sm font-semibold text-slate-700">或载入已有对局</h2>
        <div className="flex gap-2">
          <Input
            value={loadId}
            onChange={(e) => setLoadId(e.target.value)}
            placeholder="对局 ID，例如 g_demo"
          />
          <Button variant="soft" onClick={load}>
            载入
          </Button>
        </div>
        {gameId && <p className="text-xs text-slate-400">当前已保存对局：{gameId}</p>}
      </Card>
    </div>
  );
}
