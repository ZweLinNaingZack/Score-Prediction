import Link from "next/link";

import { leagueById } from "@/lib/leagues";
import type { Match } from "@/lib/types";
import TeamCrest from "./TeamCrest";

// A match that should already be under way but is still marked upcoming. Our data source (football-data.org
// free plan) can be hours behind, so say so instead of showing a kickoff time that has passed.
const GRACE_MS = 20 * 60_000;
const isOverdue = (m: Match) => m.status === "UPCOMING" && Date.now() - new Date(m.kickoff).getTime() > GRACE_MS;

export function Status({ match, compact = false }: { match: Match; compact?: boolean }) {
  if (isOverdue(match)) {
    const d = new Date(match.kickoff);
    const time = d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    return compact ? (
      <>
        <span className="text-xs font-semibold text-muted">Awaiting score</span>
        <span className="text-xs text-muted">Kicked off {time}</span>
      </>
    ) : (
      <span className="text-xs text-muted">Kicked off {time} · awaiting score</span>
    );
  }
  if (compact && match.status === "UPCOMING") {
    const d = new Date(match.kickoff);
    return (
      <>
        <span className="text-sm font-semibold tabular-nums">
          {d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
        </span>
        <span className="text-xs text-muted">
          {d.toLocaleDateString([], { weekday: "short", day: "numeric", month: "short" })}
        </span>
      </>
    );
  }
  if (match.status === "LIVE") {
    return (
      <span className="inline-flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-live">
        <span aria-hidden="true" className="h-1.5 w-1.5 animate-pulse rounded-full bg-live" />
        Live{match.minute != null && ` ${match.minute}'`}
      </span>
    );
  }
  if (match.status === "FINISHED") {
    return <span className="text-xs font-semibold uppercase tracking-wider text-muted">Full time</span>;
  }
  const d = new Date(match.kickoff);
  return (
    <span className="text-xs text-muted">
      {d.toLocaleDateString([], { weekday: "short", day: "numeric", month: "short" })}
      {" · "}
      {d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
    </span>
  );
}

export default function MatchCard({
  match,
  showLeague = false,
  featured = false,
  index = 0,
}: {
  match: Match;
  showLeague?: boolean;
  featured?: boolean;
  index?: number;
}) {
  const { home, away, score } = match;
  const label = `${home.name} ${score ? `${score.home} to ${score.away}` : "versus"} ${away.name}`;

  return (
    <Link
      href={`/match/${match.id}`}
      aria-label={label}
      style={{ "--i": index } as React.CSSProperties}
      className={`reveal block rounded-3xl border p-6 transition-colors ${
        featured
          ? "border-accent/40 bg-gradient-to-b from-accent/[0.09] to-transparent sm:p-8"
          : "border-line bg-surface hover:bg-surface-hover"
      }`}
    >
      <div className="mb-6 flex items-center justify-between">
        <span className="text-xs uppercase tracking-widest text-muted">
          {showLeague ? leagueById(match.leagueId)?.name : ""}
        </span>
        <Status match={match} />
      </div>

      <div className="grid grid-cols-[1fr_auto_1fr] items-center gap-4">
        <div className="flex flex-col items-center gap-3 text-center">
          <TeamCrest team={home} large={featured} />
          <span className="font-medium">{home.name}</span>
        </div>
        <span
          className={`font-display tabular-nums leading-none tracking-tight ${
            featured ? "text-7xl sm:text-8xl" : "text-5xl"
          }`}
        >
          {score ? (
            <>
              {score.home}
              <span className="px-2 text-muted">:</span>
              {score.away}
            </>
          ) : (
            <span className="text-3xl text-muted">VS</span>
          )}
        </span>
        <div className="flex flex-col items-center gap-3 text-center">
          <TeamCrest team={away} large={featured} />
          <span className="font-medium">{away.name}</span>
        </div>
      </div>

      <p className="mt-6 border-t border-line pt-4 text-center text-sm text-accent">View prediction ›</p>
    </Link>
  );
}
