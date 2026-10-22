"use client";

import Link from "next/link";
import { useState } from "react";

import { unlockMatch, usingMockData } from "@/lib/api";
import { useSession } from "@/lib/auth";
import { leagueById, modelLabel } from "@/lib/leagues";
import { useMatches } from "@/lib/useMatches";
import type { Match, Prediction } from "@/lib/types";
import { Status } from "./MatchCard";
import { MarketCompare, MarketOdds } from "./MarketOdds";
import { MockBanner, StateMessage } from "./States";
import TeamCrest from "./TeamCrest";

function LockIcon() {
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="4" y="11" width="16" height="10" rx="2" />
      <path d="M8 11V7a4 4 0 0 1 8 0v4" />
    </svg>
  );
}

function Scoreboard({ match }: { match: Match }) {
  const { home, away, score } = match;
  const league = leagueById(match.leagueId);
  const kickoff = new Date(match.kickoff);

  return (
    <section
      aria-label="Match score"
      className="relative overflow-hidden rounded-[2rem] border border-accent/30 bg-gradient-to-b from-accent/[0.12] via-accent/[0.03] to-transparent px-4 py-8 sm:px-10 sm:py-12"
    >
      <div aria-hidden="true" className="hero-glow pointer-events-none absolute inset-0" />
      <div className="relative">
        <div className="mb-8 flex flex-wrap items-center justify-between gap-2 text-xs uppercase tracking-widest text-muted">
          <span>{league?.name}</span>
          <Status match={match} />
        </div>

        <div className="grid grid-cols-[1fr_auto_1fr] items-center gap-3 sm:gap-8">
          <div className="flex flex-col items-center gap-4 text-center">
            <TeamCrest team={home} size="xl" />
            <h2 className="text-lg font-semibold leading-tight sm:text-2xl">{home.name}</h2>
          </div>

          <div className="text-center">
            {score ? (
              <div
                className="font-display text-6xl leading-none tracking-tight tabular-nums text-accent sm:text-8xl"
                aria-label={`${score.home} to ${score.away}`}
              >
                {score.home}
                <span className="px-2 text-muted sm:px-4">:</span>
                {score.away}
              </div>
            ) : (
              <div className="font-display text-5xl leading-none text-muted sm:text-6xl">VS</div>
            )}
            <p className="mt-3 text-xs text-muted">
              {kickoff.toLocaleDateString([], { weekday: "long", day: "numeric", month: "long" })}
              <br />
              {kickoff.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
            </p>
          </div>

          <div className="flex flex-col items-center gap-4 text-center">
            <TeamCrest team={away} size="xl" />
            <h2 className="text-lg font-semibold leading-tight sm:text-2xl">{away.name}</h2>
          </div>
        </div>
      </div>
    </section>
  );
}

function PredictionCard({ p, match }: { p: Prediction; match: Match }) {
  const { score } = match;
  const done = match.status === "FINISHED" && score;
  const exact = done && p.home === score.home && p.away === score.away;
  const pct = Math.round(p.confidence * 100);

  return (
    <li className={`rounded-2xl border p-5 ${exact ? "border-accent/60 bg-accent/[0.07]" : "border-line bg-surface"}`}>
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold uppercase tracking-widest text-muted">{modelLabel(p.model)}</h3>
        {exact && <span className="rounded-full bg-accent px-2 py-0.5 text-xs font-semibold text-on-accent">Exact score</span>}
      </div>
      <div className="mt-2 font-display text-5xl tabular-nums leading-none">
        {p.home}
        <span className="px-1.5 text-muted">-</span>
        {p.away}
      </div>
      <div className="mt-4">
        <div className="flex justify-between text-xs text-muted">
          <span>Confidence</span>
          <span className="tabular-nums">{pct}%</span>
        </div>
        <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-surface-hover" role="presentation">
          <div className="h-full rounded-full bg-accent" style={{ width: `${pct}%` }} />
        </div>
      </div>
      {p.reason && (
        <div className="mt-4 border-t border-line pt-4">
          <h4 className="text-xs font-semibold uppercase tracking-widest text-accent">Why</h4>
          <p className="mt-1 text-sm leading-relaxed text-foreground/90">{p.reason}</p>
        </div>
      )}
    </li>
  );
}

function Predictions({ match, reload }: { match: Match; reload: () => void }) {
  const session = useSession();
  const [demoUnlocked, setDemoUnlocked] = useState(false); // mock data only: nothing is withheld
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const models = match.predictionModels;
  if (models.length === 0) {
    return <StateMessage>No predictions for this match yet.</StateMessage>;
  }

  if ((match.unlocked || (usingMockData && demoUnlocked)) && match.predictions.length > 0) {
    const model = match.predictions.find((p) => p.chances)?.chances;
    return (
      <div className="reveal space-y-4">
        <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {match.predictions.map((p) => (
            <PredictionCard key={p.model} p={p} match={match} />
          ))}
        </ul>
        {match.odds && model && <MarketCompare match={match} odds={match.odds} model={model} />}
      </div>
    );
  }

  async function unlock() {
    setBusy(true);
    setError(null);
    try {
      await unlockMatch(match.id);
      reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not unlock. Try again.");
    } finally {
      setBusy(false);
    }
  }

  const button =
    "inline-flex min-h-11 items-center gap-2 rounded-full bg-accent px-6 font-semibold text-on-accent transition-transform hover:scale-[1.03] active:scale-[0.98] disabled:opacity-60";

  return (
    <div className="relative overflow-hidden rounded-3xl border border-line">
      {/* blurred placeholders so the lock has something to hide; carries no real data */}
      <div aria-hidden="true" className="grid gap-3 p-5 opacity-40 blur-md select-none sm:grid-cols-2 lg:grid-cols-3">
        {models.map((m) => (
          <div key={m} className="rounded-2xl border border-line bg-surface p-5">
            <div className="h-3 w-16 rounded bg-foreground/30" />
            <div className="mt-3 h-10 w-24 rounded bg-foreground/30" />
            <div className="mt-4 h-2 w-full rounded bg-foreground/20" />
          </div>
        ))}
      </div>
      <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 bg-background/60 p-6 text-center">
        <p className="text-sm text-muted">
          {models.length === 1 ? "1 prediction is ready" : `${models.length} predictions are ready`}:{" "}
          {models.map((m) => modelLabel(m)).join(", ")}.
        </p>
        {session || usingMockData ? (
          <button onClick={usingMockData ? () => setDemoUnlocked(true) : unlock} disabled={busy} className={button}>
            <LockIcon />
            {busy ? "Unlocking…" : "Unlock prediction"}
          </button>
        ) : (
          <Link href="/login" className={button}>
            <LockIcon />
            Sign in to unlock
          </Link>
        )}
        {error && (
          <p role="alert" className="text-sm text-live">
            {error}
          </p>
        )}
      </div>
    </div>
  );
}

export default function MatchDetail({ id }: { id: number }) {
  const { matches, error, refreshSeconds, reload } = useMatches();
  const match = matches?.find((m) => m.id === id);

  return (
    <div className="space-y-8">
      <MockBanner />
      <Link
        href={match ? `/league/${match.leagueId}` : "/matches"}
        className="inline-flex min-h-11 items-center text-sm text-muted transition-colors hover:text-foreground"
      >
        ← Back to matches
      </Link>

      {error && !matches && <StateMessage tone="error">Can&apos;t reach the API. Retrying every {refreshSeconds}s.</StateMessage>}
      {matches === null && !error && <StateMessage>Loading match…</StateMessage>}
      {matches && !match && <StateMessage>This match is no longer listed.</StateMessage>}

      {match && (
        <>
          <Scoreboard match={match} />
          {match.odds && <MarketOdds match={match} odds={match.odds} />}
          <section aria-labelledby="pred-heading" className="space-y-4">
            <h2 id="pred-heading" className="font-display text-3xl tracking-tight">Predictions</h2>
            <Predictions match={match} reload={reload} />
          </section>
        </>
      )}
    </div>
  );
}
