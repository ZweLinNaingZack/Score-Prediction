import Link from "next/link";

import { leagueById } from "@/lib/leagues";
import type { Match } from "@/lib/types";
import { Status } from "./MatchCard";
import TeamCrest from "./TeamCrest";

// Ranked list row, used for the upcoming list. Opens the match page.
export default function MatchRow({ match, rank }: { match: Match; rank: number }) {
  return (
    <li style={{ "--i": rank } as React.CSSProperties} className="reveal">
      <Link
        href={`/match/${match.id}`}
        className="grid grid-cols-[auto_1fr_auto] items-center gap-x-5 rounded-2xl border border-line bg-surface p-5 transition-colors hover:bg-surface-hover"
      >
        <span aria-hidden="true" className="font-display text-4xl leading-none text-accent">
          {rank}
        </span>
        <div>
          <div className="flex items-center gap-3 text-lg font-semibold leading-snug">
            <TeamCrest team={match.home} size="sm" />
            <span>
              {match.home.name} <span className="font-normal text-muted">vs</span> {match.away.name}
            </span>
            <TeamCrest team={match.away} size="sm" />
          </div>
          <div className="mt-1 flex flex-wrap items-center gap-x-2 text-xs text-muted">
            <span className="uppercase tracking-widest">{leagueById(match.leagueId)?.name}</span>
            <span aria-hidden="true">·</span>
            <Status match={match} />
          </div>
        </div>
        <span aria-hidden="true" className="text-muted">›</span>
      </Link>
    </li>
  );
}
