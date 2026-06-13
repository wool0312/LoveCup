import { useSyncExternalStore } from "react";

interface AppState {
  gameId: string | null;
  activePlayerId: string | null;
}

const KEY = "lovecup_state";

function read(): AppState {
  try {
    const raw = localStorage.getItem(KEY);
    if (raw) return JSON.parse(raw) as AppState;
  } catch {
    /* ignore */
  }
  return { gameId: null, activePlayerId: null };
}

let state = read();
const listeners = new Set<() => void>();

function emit() {
  localStorage.setItem(KEY, JSON.stringify(state));
  listeners.forEach((l) => l());
}

export function setGameId(gameId: string | null) {
  state = { ...state, gameId };
  emit();
}

export function setActivePlayer(activePlayerId: string | null) {
  state = { ...state, activePlayerId };
  emit();
}

export function useAppState(): AppState {
  return useSyncExternalStore(
    (cb) => {
      listeners.add(cb);
      return () => listeners.delete(cb);
    },
    () => state
  );
}
