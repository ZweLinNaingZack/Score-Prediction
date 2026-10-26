"use client";

import { useMemo, useState } from "react";

import { useMatches } from "@/lib/useMatches";
import { LEAGUES } from "@/lib/leagues";
import type { MatchStatus } from "@/lib/types";
import DateStrip, { buildDays, dayKey } from "./DateStrip";
import LeagueLogo from "./LeagueLogo";
import MatchListItem from "./MatchListItem";
import { MockBanner, StateMessage } from "./States";

type StatusFilter = "ALL" | MatchStatus;

const STATUS_TABS: { id: StatusFilter; label: string }[] = [
  { id: "ALL", label: "All" },
  { id: "LIVE", label: "Live" },
  { id: "UPCOMING", label: "Upcoming" },
  { id: "FINISHED", label: "Finished" },
];

const tab = (active: boolean) =>
  `min-h-11 whitespace-nowrap border-b-2 text-sm transition-colors ${
    active
      ? "border-accent text-foreground"
      : "border-transparent text-muted hover:text-foreground"
  }`;

const pill = (active: boolean) =>
  `min-h-11 whitespace-nowrap rounded-full border px-4 text-sm transition-colors ${
    active
      ? "border-accent bg-accent font-medium text-on-accent"
      : "border-line text-muted hover:text-foreground"
  }`;

export default function MatchesBoard({ fixedLeagueId }: { fixedLeagueId?: number }) {
  const { matches, error, refreshSeconds } = useMatches();
  const [status, setStatus] = useState<StatusFilter>("ALL");
  const [leagueId, setLeagueId] = useState<number | null>(null);
  const [pickedDay, setPickedDay] = useState<string | null>(null);

  const activeLeague = fixedLeagueId ?? leagueId;
  const liveCount = matches?.filter((m) => m.status === "LIVE").length ?? 0;

  // The dots on the date strip follow the league and status filters.
  const days = useMemo(
    () =>
      matches
        ? buildDays(
            matches
              .filter(
                (m) =>
                  (activeLeague === null || m.leagueId === activeLeague) &&
                  (status === "ALL" || m.status === status),
              )
              .map((m) => m.kickoff),
          )
        : [],
    [matches, activeLeague, status],
  );
  // No clock read until matches load: the server prerender must not depend on the current time.
  const day = pickedDay ?? (matches ? dayKey(new Date()) : "");
  // The last day we hold any match for (YYYY-MM-DD, local). Days after it have not been loaded, which is
  // different from a day that simply has no matches.
  const lastLoadedDay = useMemo(() => {
    if (!matches?.length) return "";
    return dayKey(new Date(Math.max(...matches.map((m) => Date.parse(m.kickoff)))));
  }, [matches]);

  const groups = useMemo(() => {
    if (!matches) return [];
    const order: Record<MatchStatus, number> = { LIVE: 0, UPCOMING: 1, FINISHED: 2 };
    return LEAGUES.filter((l) => activeLeague === null || l.id === activeLeague)
      .map((league) => ({
        league,
        matches: matches
          .filter(
            (m) =>
              m.leagueId === league.id &&
              (status === "ALL" || m.status === status) &&
              dayKey(new Date(m.kickoff)) === day,
          )
          .sort(
            (a, b) =>
              order[a.status] - order[b.status] ||
              new Date(a.kickoff).getTime() - new Date(b.kickoff).getTime(),
          ),
      }))
      .filter((g) => g.matches.length > 0);
  }, [matches, status, activeLeague, day]);

  return (
    <div className="space-y-8">
      <MockBanner />

      <div role="group" aria-label="Filter by status" className="flex gap-6 border-b border-line">
        {STATUS_TABS.map((s) => (
          <button
            key={s.id}
            onClick={() => setStatus(s.id)}
            aria-pressed={status === s.id}
            className={tab(status === s.id)}
          >
            {s.label}
            {s.id === "LIVE" && liveCount > 0 && (
              <span className="ml-1.5 text-xs text-live">{liveCount}<span className="sr-only"> live now</span></span>
            )}
          </button>
        ))}
      </div>

      {fixedLeagueId === undefined && (
        <div role="group" aria-label="Filter by league" className="-mx-5 flex gap-2 overflow-x-auto px-5 pb-1">
          <button
            onClick={() => setLeagueId(null)}
            aria-pressed={leagueId === null}
            className={pill(leagueId === null)}
          >
            All leagues
          </button>
          {LEAGUES.map((l) => (
            <button
              key={l.id}
              onClick={() => setLeagueId(l.id)}
              aria-pressed={leagueId === l.id}
              className={pill(leagueId === l.id)}
            >
              {l.name}
            </button>
          ))}
        </div>
      )}

      {matches && <DateStrip days={days} selected={day} onSelect={setPickedDay} />}

      {error && <StateMessage tone="error">Can&apos;t reach the API. Retrying every {refreshSeconds}s.</StateMessage>}
      {matches === null && !error && <StateMessage>Loading matches…</StateMessage>}
      {matches && groups.length === 0 && (
        <StateMessage>
          {lastLoadedDay && day > lastLoadedDay
            ? "Fixtures for this day are not loaded yet. We load about 9 days ahead, and predictions follow within hours."
            : "No matches on this day."}
        </StateMessage>
      )}

      {groups.map(({ league, matches }) => (
        <section key={league.id} className="space-y-4">
          <div className="flex items-baseline justify-between">
            <h2 className="flex items-center gap-3 font-display text-3xl tracking-tight">
              <LeagueLogo league={league} size="sm" />
              {league.name}
            </h2>
            <span className="text-xs text-muted">
              {league.country} · {league.category}
            </span>
          </div>
          <ul className="divide-y divide-line overflow-hidden rounded-2xl border border-line bg-surface">
            {matches.map((m, i) => (
              <MatchListItem key={m.id} match={m} index={Math.min(i, 8)} />
            ))}
          </ul>
        </section>
      ))}
    </div>
  );
}
