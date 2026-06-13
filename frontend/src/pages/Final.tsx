import { useEffect, useState } from "react";
import { api } from "../api";
import type { Game, Standings } from "../types";
import { Banner, Card, Pill } from "../ui";

const CEREMONY = [
  "正式宣布 Love Cup 2026 最终比赛结果",
  "宣布冠军姓名及双方最终积分",
  "为冠军进行简单颁奖",
  "向冠军表示祝贺",
  "双方共同拍摄冠军合影或纪念视频",
];

export default function Final({ game }: { game: Game }) {
  const [data, setData] = useState<Standings | null>(null);
  useEffect(() => {
    api.standings(game.id).then(setData);
  }, [game.id]);

  if (!data) return <Banner tone="info">加载中…</Banner>;

  const nameOf = (id: string) => game.players.find((p) => p.id === id)?.name ?? id;
  const champNames = data.champion_ids.map(nameOf).join(" 与 ");
  const loser = game.players.find((p) => !data.champion_ids.includes(p.id));
  const host = loser ?? game.players[0]; // 主持人为积分较低者

  return (
    <div className="space-y-3">
      <Card className="text-center">
        <div className="text-4xl">🏆</div>
        <h2 className="mt-1 text-lg font-bold text-brand">
          {data.is_tie ? "并列冠军" : "总冠军"}
        </h2>
        <p className="mt-1 text-2xl font-semibold">{champNames}</p>
        <div className="mt-3 flex justify-center gap-4 text-sm">
          {game.players.map((p) => (
            <div key={p.id}>
              <div className="text-slate-400">{p.name}</div>
              <div className="font-mono font-semibold">
                {data.players[p.id].final_score}
              </div>
            </div>
          ))}
        </div>
        {data.margin_ratio && (
          <p className="mt-2 text-xs text-slate-400">
            分差比例 {(Number(data.margin_ratio) * 100).toFixed(1)}%
          </p>
        )}
      </Card>

      <Card className="space-y-2">
        <h3 className="text-sm font-semibold text-slate-700">奖励</h3>
        <p className="text-sm text-slate-600">
          🎁 日本旅行礼物奖励（预算上限 {game.japan_budget_cny} 元人民币）
        </p>
        <p className="text-sm text-slate-600">⭐ 一项赛后自定的冠军特权</p>
      </Card>

      {data.blowout && (
        <Card className="space-y-1 border-amber-200 bg-amber-50">
          <div className="flex items-center gap-2">
            <Pill tone="amber">大胜（分差 ≥ 25%）</Pill>
          </div>
          <p className="text-sm text-amber-800">
            追加环节：失败者复盘报告（≥500 字，当面完整朗读）＋ 冠军夸夸（≥1 分钟）。
          </p>
        </Card>
      )}

      <Card className="space-y-2">
        <h3 className="text-sm font-semibold text-slate-700">冠军颁奖仪式</h3>
        <p className="text-xs text-slate-500">
          主持人：{host.name}（最终积分较低者）。仪式至少包括以下环节：
        </p>
        <ol className="space-y-1 text-sm text-slate-600">
          {CEREMONY.map((c, i) => (
            <li key={i} className="flex gap-2">
              <span className="text-brand">{i + 1}.</span>
              <span>{c}</span>
            </li>
          ))}
        </ol>
        <p className="text-xs text-slate-400">
          以双方自愿、轻松娱乐、私人纪念为原则；任何视频、照片与复盘报告未经双方同意不得公开。
        </p>
      </Card>
    </div>
  );
}
