"use client";

import Link from "next/link";

import { hottestLive, hottestUpcoming } from "@/lib/hot";
import { LEAGUES } from "@/lib/leagues";
import { useMatches } from "@/lib/useMatches";
import LeagueLogo from "./LeagueLogo";
import MatchCard from "./MatchCard";
import MatchRow from "./MatchRow";
import { MockBanner, StateMessage } from "./States";

function SectionHeading({ id, title, hint }: { id: string; title: string; hint: string }) {
  return (
    <div className="mb-6 flex items-end justify-between gap-4">
      <div>
        <h2 id={id} className="font-display text-4xl tracking-tight">{title}</h2>
        <p className="text-sm text-muted">{hint}</p>
      </div>
      <Link
        href="/matches"
        className="flex min-h-11 items-center whitespace-nowrap text-sm text-muted transition-colors hover:text-foreground"
      >
        All matches →
      </Link>
    </div>
  );
}

export default function Landing() {
  const { matches, error, refreshSeconds } = useMatches();

  const liveByLeague = (id: number) =>
    matches?.filter((m) => m.leagueId === id && m.status === "LIVE").length ?? 0;

  const live = matches ? hottestLive(matches) : [];
  const [featured, ...restLive] = live;
  const upcoming = matches ? hottestUpcoming(matches) : [];

  return (
    <div className="space-y-24">
      <section className="space-y-5 pt-8">
        <h1 className="max-w-3xl font-display text-6xl leading-[0.95] tracking-tight sm:text-8xl">
          Every score, <span className="text-accent">called by data.</span>
        </h1>
        <p className="max-w-xl text-lg text-muted">
          Predictions from our own model, trained on thousands of real matches and tracked
          against real results.
        </p>
        <MockBanner />
      </section>

      <section aria-labelledby="leagues-heading">
        <h2 id="leagues-heading" className="mb-6 font-display text-4xl tracking-tight">
          Choose a league
        </h2>
        <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
          {LEAGUES.map((l, i) => {
            const liveCount = liveByLeague(l.id);
            return (
              <Link
                key={l.id}
                href={`/league/${l.id}`}
                style={{ "--i": i } as React.CSSProperties}
                className="reveal group relative flex min-h-36 flex-col justify-between overflow-hidden rounded-2xl border border-line bg-surface p-4 transition-colors hover:border-accent/50 hover:bg-surface-hover"
              >
                <LeagueLogo league={l} size="lg" />
                <div>
                  <div className="font-semibold leading-snug">{l.name}</div>
                  <div className="mt-1 flex flex-wrap items-center gap-x-2 text-xs text-muted">
                    <span>{l.category}</span>
                    {liveCount > 0 && (
                      <span className="inline-flex items-center gap-1 font-medium text-live">
                        <span
                          aria-hidden="true"
                          className="h-1.5 w-1.5 animate-pulse rounded-full bg-live"
                        />
                        {liveCount} live
                      </span>
                    )}
                  </div>
                </div>
              </Link>
            );
          })}
        </div>
      </section>

      {error && (
        <StateMessage tone="error">
          Can&apos;t reach the API. Retrying every {refreshSeconds}s.
        </StateMessage>
      )}

      <section aria-labelledby="live-heading">
        <SectionHeading id="live-heading" title="Hottest live" hint="The matches worth watching right now." />
        {matches === null ? (
          <StateMessage>Loading…</StateMessage>
        ) : !featured ? (
          <StateMessage>No live matches at the moment.</StateMessage>
        ) : (
          <div className="space-y-4">
            <MatchCard match={featured} showLeague featured />
            {restLive.length > 0 && (
              <div className="grid gap-4 md:grid-cols-2">
                {restLive.map((m, i) => (
                  <MatchCard key={m.id} match={m} showLeague index={i + 1} />
                ))}
              </div>
            )}
          </div>
        )}
      </section>

      <section aria-labelledby="upcoming-heading">
        <SectionHeading id="upcoming-heading" title="Hottest upcoming" hint="Biggest fixtures kicking off soon." />
        {matches === null ? (
          <StateMessage>Loading…</StateMessage>
        ) : upcoming.length === 0 ? (
          <StateMessage>No upcoming matches.</StateMessage>
        ) : (
          <ol className="space-y-3">
            {upcoming.map((m, i) => (
              <MatchRow key={m.id} match={m} rank={i + 1} />
            ))}
          </ol>
        )}
      </section>
    </div>
  );
}
