import { useEffect, useState } from "react";
import { NavLink, Navigate, Route, HashRouter, Routes } from "react-router-dom";
import { api } from "./api";
import { setActivePlayer, setGameId, useAppState } from "./store";
import type { Game } from "./types";
import Setup from "./pages/Setup";
import MatchDay from "./pages/MatchDay";
import Odds from "./pages/Odds";
import Standings from "./pages/Standings";
import History from "./pages/History";
import Final from "./pages/Final";

const NAV = [
  { to: "/matchday", label: "比赛日", icon: "⚽" },
  { to: "/odds", label: "赔率", icon: "📈" },
  { to: "/standings", label: "积分", icon: "🏆" },
  { to: "/history", label: "历史", icon: "📋" },
  { to: "/final", label: "颁奖", icon: "🥇" },
];

function PinSettings({ game, onClose }: { game: Game; onClose: () => void }) {
  const [adminPin, setAdminPin] = useState("");
  const [newAdminPin, setNewAdminPin] = useState("");
  const [player1Pin, setPlayer1Pin] = useState("");
  const [player2Pin, setPlayer2Pin] = useState("");
  const [err, setErr] = useState<string | null>(null);
  const [ok, setOk] = useState<string | null>(null);

  async function save() {
    setErr(null);
    setOk(null);
    if (adminPin.trim().length < 4) {
      setErr("请输入当前管理 PIN");
      return;
    }
    if (!newAdminPin.trim() && !player1Pin.trim() && !player2Pin.trim()) {
      setErr("至少填写一个新 PIN");
      return;
    }
    try {
      const result = await api.updatePins(game.id, {
        admin_pin: adminPin.trim(),
        new_admin_pin: newAdminPin.trim() || undefined,
        player1_pin: player1Pin.trim() || undefined,
        player2_pin: player2Pin.trim() || undefined,
      });
      setOk(`已更新：${result.updated.join("、")}`);
      setNewAdminPin("");
      setPlayer1Pin("");
      setPlayer2Pin("");
    } catch (e) {
      setErr(String(e));
    }
  }

  return (
    <div className="fixed inset-0 z-20 flex items-center justify-center bg-slate-900/20 p-4">
      <div className="w-full max-w-sm rounded-lg border border-slate-200 bg-white p-4 shadow-xl">
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-slate-700">PIN 设置</h2>
          <button onClick={onClose} className="rounded px-2 py-1 text-sm text-slate-400 hover:bg-slate-100">
            关闭
          </button>
        </div>
        <div className="space-y-2 text-xs">
          <label className="block">
            <span className="mb-1 block text-slate-500">当前管理 PIN</span>
            <input
              type="password"
              value={adminPin}
              onChange={(e) => setAdminPin(e.target.value)}
              className="w-full rounded-lg border border-slate-200 px-3 py-2"
            />
          </label>
          <label className="block">
            <span className="mb-1 block text-slate-500">新管理 PIN（可选）</span>
            <input
              type="password"
              value={newAdminPin}
              onChange={(e) => setNewAdminPin(e.target.value)}
              className="w-full rounded-lg border border-slate-200 px-3 py-2"
            />
          </label>
          <label className="block">
            <span className="mb-1 block text-slate-500">{game.players[0].name} 新 PIN（可选）</span>
            <input
              type="password"
              value={player1Pin}
              onChange={(e) => setPlayer1Pin(e.target.value)}
              className="w-full rounded-lg border border-slate-200 px-3 py-2"
            />
          </label>
          <label className="block">
            <span className="mb-1 block text-slate-500">{game.players[1].name} 新 PIN（可选）</span>
            <input
              type="password"
              value={player2Pin}
              onChange={(e) => setPlayer2Pin(e.target.value)}
              className="w-full rounded-lg border border-slate-200 px-3 py-2"
            />
          </label>
          {err && <div className="rounded-lg bg-red-50 p-2 text-red-600">{err}</div>}
          {ok && <div className="rounded-lg bg-green-50 p-2 text-green-700">{ok}</div>}
          <button onClick={save} className="w-full rounded-lg bg-brand px-3 py-2 font-semibold text-white">
            保存 PIN
          </button>
        </div>
      </div>
    </div>
  );
}

function TopBar({ game, onExit }: { game: Game | null; onExit: () => void }) {
  const { activePlayerId } = useAppState();
  const [copied, setCopied] = useState(false);
  const [showMenu, setShowMenu] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [showPinSettings, setShowPinSettings] = useState(false);
  if (!game) return null;

  function copyId() {
    navigator.clipboard.writeText(game!.id).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    });
  }

  async function deleteGame() {
    const adminPin = window.prompt("请输入管理 PIN，确认删除该对局。旧对局如未设置 PIN，可留空。");
    if (adminPin === null) return;
    try {
      await api.deleteGame(game!.id, adminPin);
      setGameId(null);
      setActivePlayer(null);
    } catch (e) {
      alert(`删除失败：${String(e)}`);
    }
  }

  return (
    <div className="border-b border-emerald-900/10 bg-white/95 px-4 py-3 shadow-sm shadow-emerald-900/5">
      <div className="flex items-center justify-between gap-2">
        <div>
          <div className="flex items-center gap-2 text-sm font-bold text-cup-deep">
            <span className="inline-flex h-7 w-7 items-center justify-center rounded-full bg-cup-deep text-sm text-cup-gold">
              ⚽
            </span>
            <span>Love Cup 2026</span>
          </div>
          <div className="mt-0.5 text-[10px] font-medium uppercase tracking-[0.18em] text-emerald-700">
            World Cup Match Center
          </div>
        </div>
        <div className="flex items-center gap-1 text-xs">
          <span className="text-slate-400">当前玩家</span>
          {game.players.map((p) => (
            <button
              key={p.id}
              onClick={() => setActivePlayer(p.id)}
              className={`rounded-full px-2 py-1 font-medium ${
                activePlayerId === p.id
                  ? "bg-cup-deep text-white shadow-sm"
                  : "bg-emerald-50 text-emerald-800"
              }`}
            >
              {p.name}
            </button>
          ))}
        </div>
      </div>
      <div className="mt-1 flex items-center justify-between text-xs">
        <div className="flex items-center gap-1 text-slate-400">
          <span>对局 ID：{game.id}</span>
          <button onClick={copyId} className="rounded bg-emerald-50 px-1.5 py-0.5 text-emerald-700 hover:bg-emerald-100">
            {copied ? "已复制" : "复制"}
          </button>
        </div>
        <div className="relative">
          <button onClick={() => setShowMenu(!showMenu)} className="rounded bg-emerald-50 px-2 py-0.5 text-emerald-700 hover:bg-emerald-100">
            ···
          </button>
          {showMenu && (
            <div className="absolute right-0 top-6 z-10 w-28 rounded-lg border border-slate-200 bg-white py-1 shadow-lg">
              <button onClick={() => { onExit(); setShowMenu(false); }} className="block w-full px-3 py-1.5 text-left text-sm text-slate-600 hover:bg-slate-50">
                退出对局
              </button>
              <button onClick={() => { setShowPinSettings(true); setShowMenu(false); }} className="block w-full px-3 py-1.5 text-left text-sm text-slate-600 hover:bg-slate-50">
                PIN 设置
              </button>
              {!confirmDelete ? (
                <button onClick={() => setConfirmDelete(true)} className="block w-full px-3 py-1.5 text-left text-sm text-red-500 hover:bg-red-50">
                  删除对局
                </button>
              ) : (
                <button onClick={() => { deleteGame(); setShowMenu(false); }} className="block w-full px-3 py-1.5 text-left text-sm font-semibold text-red-600 hover:bg-red-50">
                  确认删除
                </button>
              )}
            </div>
          )}
        </div>
      </div>
      {showPinSettings && <PinSettings game={game} onClose={() => setShowPinSettings(false)} />}
    </div>
  );
}

function Shell() {
  const { gameId, activePlayerId } = useAppState();
  const [game, setGame] = useState<Game | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    let cancelled = false;
    if (!gameId) {
      queueMicrotask(() => {
        if (!cancelled) setGame(null);
      });
      return () => {
        cancelled = true;
      };
    }
    queueMicrotask(() => {
      if (!cancelled) setLoading(true);
    });
    api
      .getGame(gameId)
      .then((g) => {
        if (cancelled) return;
        setGame(g);
        if (!activePlayerId) setActivePlayer(g.players[0].id);
      })
      .catch(() => {
        if (cancelled) return;
        setGame(null);
        setGameId(null);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [gameId, activePlayerId]);

  if (!gameId) {
    return (
      <Routes>
        <Route path="/setup" element={<Setup />} />
        <Route path="*" element={<Navigate to="/setup" replace />} />
      </Routes>
    );
  }

  if (loading || !game) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <p className="text-sm text-slate-400">加载中…</p>
      </div>
    );
  }

  return (
    <div className="mx-auto flex min-h-full max-w-xl flex-col">
      <TopBar game={game} onExit={() => { setGameId(null); setActivePlayer(null); }} />
      <main className="flex-1 p-4 pb-24">
        <Routes>
          <Route path="/setup" element={<Setup />} />
          <Route path="/matchday" element={<MatchDay game={game} />} />
          <Route path="/odds" element={<Odds game={game} />} />
          <Route path="/standings" element={<Standings game={game} />} />
          <Route path="/history" element={<History game={game} />} />
          <Route path="/final" element={<Final game={game} />} />
          <Route path="*" element={<Navigate to="/matchday" replace />} />
        </Routes>
      </main>
      <nav className="fixed inset-x-0 bottom-0 mx-auto flex max-w-xl justify-around border-t border-emerald-900/10 bg-white/95 px-2 py-2 shadow-[0_-10px_30px_rgba(6,78,59,0.08)] backdrop-blur">
        {NAV.map((n) => (
          <NavLink
            key={n.to}
            to={n.to}
            className={({ isActive }) =>
              `flex min-w-14 flex-col items-center gap-0.5 rounded-lg px-2 py-1 text-xs font-medium ${
                isActive ? "bg-emerald-50 text-brand" : "text-slate-400"
              }`
            }
          >
            <span className="text-base leading-none">{n.icon}</span>
            <span>{n.label}</span>
          </NavLink>
        ))}
      </nav>
    </div>
  );
}

export default function App() {
  return (
    <HashRouter>
      <Shell />
    </HashRouter>
  );
}
