"use client";

import { useEffect, useState } from "react";

import { fetchLeaderboard } from "@/lib/api";
import { modelLabel } from "@/lib/leagues";
import type { LeaderboardEntry } from "@/lib/types";
import { StateMessage } from "./States";

const pct = (n: number, total: number) => (total ? Math.round((n / total) * 100) : 0);

function Stat({ value, label, hint }: { value: string; label: string; hint: string }) {
  return (
    <div>
      <div className="font-display text-6xl leading-none tabular-nums tracking-tight sm:text-7xl">{value}</div>
      <div className="mt-3 text-sm font-medium">{label}</div>
      <div className="text-xs text-muted">{hint}</div>
    </div>
  );
}

// How the model has done on finished matches it predicted before kickoff.
export default function Leaderboard() {
  const [rows, setRows] = useState<LeaderboardEntry[] | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    fetchLeaderboard().then(setRows).catch(() => setError(true));
  }, []);

  if (error) return <StateMessage tone="error">Couldn&apos;t load the track record.</StateMessage>;
  if (!rows) return <StateMessage>Loading…</StateMessage>;

  const sorted = [...rows].sort((a, b) => pct(b.correctOutcomes, b.played) - pct(a.correctOutcomes, a.played));

  return (
    <div className="space-y-6">
      {sorted.map((r) => {
        const outcome = pct(r.correctOutcomes, r.played);
        return (
          <section
            key={r.model}
            aria-label={`${modelLabel(r.model)} results`}
            className="relative overflow-hidden rounded-[2rem] border border-accent/30 bg-gradient-to-b from-accent/[0.10] via-accent/[0.03] to-transparent p-6 sm:p-10"
          >
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-semibold uppercase tracking-widest text-muted">{modelLabel(r.model)}</h2>
              <span className="text-xs text-muted tabular-nums">{r.played} finished matches</span>
            </div>
            {r.played === 0 ? (
              <p className="mt-6 text-muted">No finished predictions yet. Results appear after the first matches end.</p>
            ) : (
              <>
                <div className="mt-8 grid gap-8 sm:grid-cols-3">
                  <Stat value={`${outcome}%`} label="Right result" hint="Home win, draw or away win" />
                  <Stat value={`${pct(r.exactScores, r.played)}%`} label="Exact score" hint="Called the score on the nose" />
                  <Stat value={String(r.correctOutcomes)} label="Right calls" hint={`out of ${r.played}`} />
                </div>
                <div className="mt-8 h-1.5 overflow-hidden rounded-full bg-line" role="presentation">
                  <div className="h-full rounded-full bg-accent" style={{ width: `${outcome}%` }} />
                </div>
                <p className="mt-4 text-xs text-muted">
                  For comparison: always picking the home team is right about 45% of the time, and the best
                  published models reach 50-55%.
                </p>
              </>
            )}
          </section>
        );
      })}
    </div>
  );
}
