import { flagForTeam, STAGE_LABELS } from "./worldCupData";

export function TeamName({ team, className = "" }: { team: string; className?: string }) {
  const flag = flagForTeam(team);
  return (
    <span className={`inline-flex min-w-0 items-center gap-1 ${className}`}>
      <span className="truncate">{team}</span>
      {flag && <span className="flag-wave shrink-0 text-[1.05em] leading-none">{flag}</span>}
    </span>
  );
}

export function StageBadge({ stage }: { stage: string }) {
  return (
    <span className="inline-flex items-center gap-1 rounded-md bg-emerald-950 px-2 py-0.5 text-[10px] font-semibold tracking-wide text-amber-200">
      <span>{STAGE_LABELS[stage] ?? stage}</span>
    </span>
  );
}
