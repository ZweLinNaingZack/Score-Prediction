import Link from "next/link";

import type { Match } from "@/lib/types";
import { Status } from "./MatchCard";
import TeamCrest from "./TeamCrest";

// One row of the match list. Predictions are not shown here: they are behind the unlock button
// on the match page.
export default function MatchListItem({ match, index = 0 }: { match: Match; index?: number }) {
  const { home, away, score } = match;
  const label = `${home.name} ${score ? `${score.home} to ${score.away}` : "versus"} ${away.name}`;

  return (
    <li style={{ "--i": index } as React.CSSProperties} className="reveal">
      <Link
        href={`/match/${match.id}`}
        aria-label={label}
        className="grid min-h-16 grid-cols-[4.5rem_1fr_auto_1fr] items-center gap-x-3 px-3 py-3 transition-colors hover:bg-surface-hover sm:grid-cols-[6rem_1fr_auto_1fr_auto] sm:gap-x-5 sm:px-5 md:grid-cols-[6rem_1fr_auto_1fr_auto_auto]"
      >
        <span className="flex flex-col text-xs">
          <Status match={match} compact />
        </span>
        <span className="flex items-center justify-end gap-3 text-right font-medium">
          <span className="hidden sm:inline">{home.name}</span>
          <span className="sm:hidden">{home.short}</span>
          <TeamCrest team={home} size="sm" />
        </span>
        <span className="min-w-14 text-center font-display text-xl tabular-nums">
          {score ? (
            <>
              {score.home}
              <span className="px-1 text-muted">:</span>
              {score.away}
            </>
          ) : (
            <span className="text-base text-muted">vs</span>
          )}
        </span>
        <span className="flex items-center gap-3 font-medium">
          <TeamCrest team={away} size="sm" />
          <span className="hidden sm:inline">{away.name}</span>
          <span className="sm:hidden">{away.short}</span>
        </span>
        {/* market odds 1 / X / 2 (wide screens only; the match page has the full view) */}
        <span className="hidden min-w-32 justify-end gap-3 text-xs tabular-nums text-muted md:flex">
          {match.odds ? (
            <>
              <span title="Home win odds">{match.odds.home.toFixed(2)}</span>
              <span title="Draw odds">{match.odds.draw.toFixed(2)}</span>
              <span title="Away win odds">{match.odds.away.toFixed(2)}</span>
              <span className="sr-only">market odds home, draw, away</span>
            </>
          ) : null}
        </span>
        <span aria-hidden="true" className="hidden text-muted sm:inline">›</span>
      </Link>
    </li>
  );
}
