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
  { to: "/matchday", label: "比赛日" },
  { to: "/odds", label: "赔率" },
  { to: "/standings", label: "积分" },
  { to: "/history", label: "历史" },
  { to: "/final", label: "颁奖" },
];

function TopBar({ game, onExit }: { game: Game | null; onExit: () => void }) {
  const { activePlayerId } = useAppState();
  const [copied, setCopied] = useState(false);
  const [showMenu, setShowMenu] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
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
    <div className="border-b border-slate-200 bg-white px-4 py-2">
      <div className="flex items-center justify-between gap-2">
        <div className="text-sm font-semibold text-brand">Love Cup 2026</div>
        <div className="flex items-center gap-1 text-xs">
          <span className="text-slate-400">当前玩家</span>
          {game.players.map((p) => (
            <button
              key={p.id}
              onClick={() => setActivePlayer(p.id)}
              className={`rounded-full px-2 py-1 font-medium ${
                activePlayerId === p.id
                  ? "bg-brand text-white"
                  : "bg-slate-100 text-slate-600"
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
          <button onClick={copyId} className="rounded bg-slate-100 px-1.5 py-0.5 text-slate-500 hover:bg-slate-200">
            {copied ? "已复制" : "复制"}
          </button>
        </div>
        <div className="relative">
          <button onClick={() => setShowMenu(!showMenu)} className="rounded bg-slate-100 px-2 py-0.5 text-slate-500 hover:bg-slate-200">
            ···
          </button>
          {showMenu && (
            <div className="absolute right-0 top-6 z-10 w-28 rounded-lg border border-slate-200 bg-white py-1 shadow-lg">
              <button onClick={() => { onExit(); setShowMenu(false); }} className="block w-full px-3 py-1.5 text-left text-sm text-slate-600 hover:bg-slate-50">
                退出对局
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
    </div>
  );
}

function Shell() {
  const { gameId, activePlayerId } = useAppState();
  const [game, setGame] = useState<Game | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!gameId) {
      setGame(null);
      return;
    }
    setLoading(true);
    api
      .getGame(gameId)
      .then((g) => {
        setGame(g);
        if (!activePlayerId) setActivePlayer(g.players[0].id);
      })
      .catch(() => {
        setGame(null);
        setGameId(null);
      })
      .finally(() => setLoading(false));
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
      <nav className="fixed inset-x-0 bottom-0 mx-auto flex max-w-xl justify-around border-t border-slate-200 bg-white py-2">
        {NAV.map((n) => (
          <NavLink
            key={n.to}
            to={n.to}
            className={({ isActive }) =>
              `rounded-lg px-3 py-1 text-xs font-medium ${
                isActive ? "text-brand" : "text-slate-400"
              }`
            }
          >
            {n.label}
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
