"use client";

import { useState } from "react";

import { LEAGUES, TABLE_LEAGUE_IDS, zoneFor, type Zone } from "@/lib/leagues";
import type { StandingGroup, StandingRow } from "@/lib/types";
import { useStandings } from "@/lib/useStandings";
import LeagueLogo from "./LeagueLogo";
import { MockBanner, StateMessage } from "./States";
import TeamCrest from "./TeamCrest";

const pill = (active: boolean) =>
  `min-h-11 whitespace-nowrap rounded-full border px-4 text-sm transition-colors ${
    active
      ? "border-accent bg-accent font-medium text-on-accent"
      : "border-line text-muted hover:text-foreground"
  }`;

// Left edge bar and legend dot per zone.
const ZONE_BG: Record<Zone["tone"], string> = {
  gold: "bg-accent",
  light: "bg-foreground/50",
  down: "bg-down",
  warn: "bg-warn",
};

const FORM_STYLE: Record<string, string> = {
  W: "bg-accent text-on-accent",
  D: "bg-foreground/25 text-foreground",
  L: "border border-down/70 text-down",
};

function Form({ form }: { form: string }) {
  if (!form) return null;
  const words = { W: "win", D: "draw", L: "loss" } as Record<string, string>;
  return (
    <span className="inline-flex gap-1" role="img" aria-label={`Last results: ${[...form].map((c) => words[c]).join(", ")}`}>
      {[...form].map((c, i) => (
        <span
          key={i}
          aria-hidden="true"
          className={`flex h-6 w-6 items-center justify-center rounded-full text-xs font-semibold ${FORM_STYLE[c] ?? ""}`}
        >
          {c}
        </span>
      ))}
    </span>
  );
}

// Column headers. `wide` columns only show from the sm breakpoint up, `xl` ones from md.
const COLS = [
  { key: "p", label: "P", title: "Played", cls: "" },
  { key: "w", label: "W", title: "Won", cls: "hidden sm:table-cell" },
  { key: "d", label: "D", title: "Drawn", cls: "hidden sm:table-cell" },
  { key: "l", label: "L", title: "Lost", cls: "hidden sm:table-cell" },
  { key: "gf", label: "GF", title: "Goals for", cls: "hidden md:table-cell" },
  { key: "ga", label: "GA", title: "Goals against", cls: "hidden md:table-cell" },
  { key: "gd", label: "GD", title: "Goal difference", cls: "" },
];

function Table({ leagueId, group }: { leagueId: number; group: StandingGroup }) {
  const total = group.rows.length;
  const num = "px-2 py-3 text-right tabular-nums sm:px-3";

  return (
    <div className="overflow-hidden rounded-3xl border border-line bg-surface">
      <table className="w-full border-collapse text-sm">
        <caption className="sr-only">{group.name ?? "League table"}</caption>
        <thead>
          <tr className="border-b border-line text-xs uppercase tracking-widest text-muted">
            <th scope="col" className="w-12 py-3 pl-4 text-left font-medium sm:pl-5">#</th>
            <th scope="col" className="px-2 py-3 text-left font-medium">Team</th>
            {COLS.map((c) => (
              <th key={c.key} scope="col" className={`px-2 py-3 text-right font-medium sm:px-3 ${c.cls}`}>
                <abbr title={c.title} className="no-underline">{c.label}</abbr>
              </th>
            ))}
            <th scope="col" className="px-3 py-3 text-right font-semibold text-foreground sm:pr-5">
              <abbr title="Points" className="no-underline">Pts</abbr>
            </th>
            <th scope="col" className="hidden px-3 py-3 text-left font-medium lg:table-cell">Form</th>
          </tr>
        </thead>
        <tbody>
          {group.rows.map((r: StandingRow, i) => {
            const zone = zoneFor(leagueId, r.position, total);
            const leader = r.position === 1;
            return (
              <tr
                key={r.team}
                style={{ "--i": Math.min(i, 12) } as React.CSSProperties}
                className={`reveal border-b border-line/60 transition-colors last:border-0 hover:bg-surface-hover ${
                  leader ? "bg-gradient-to-r from-accent/[0.10] to-transparent" : ""
                }`}
              >
                <td className="relative py-3 pl-4 sm:pl-5">
                  {zone && (
                    <span
                      aria-hidden="true"
                      className={`absolute inset-y-2 left-0 w-1 rounded-r-full ${ZONE_BG[zone.tone]}`}
                    />
                  )}
                  <span className={`font-display text-lg tabular-nums ${leader ? "text-accent" : "text-muted"}`}>
                    {r.position}
                  </span>
                  {zone && <span className="sr-only"> ({zone.label})</span>}
                </td>
                <td className="px-2 py-2">
                  <span className="flex items-center gap-3">
                    <TeamCrest team={{ name: r.team, short: r.short, crest: r.crest }} size="sm" />
                    <span className={`truncate font-medium ${leader ? "text-foreground" : ""}`}>{r.team}</span>
                  </span>
                </td>
                <td className={`${num} text-muted`}>{r.played}</td>
                <td className={`${num} hidden text-muted sm:table-cell`}>{r.won}</td>
                <td className={`${num} hidden text-muted sm:table-cell`}>{r.draw}</td>
                <td className={`${num} hidden text-muted sm:table-cell`}>{r.lost}</td>
                <td className={`${num} hidden text-muted md:table-cell`}>{r.goalsFor}</td>
                <td className={`${num} hidden text-muted md:table-cell`}>{r.goalsAgainst}</td>
                <td className={`${num} text-muted`}>
                  {r.goalDifference > 0 ? `+${r.goalDifference}` : r.goalDifference}
                </td>
                <td className={`px-3 py-3 text-right font-display text-xl tabular-nums sm:pr-5 ${leader ? "text-accent" : ""}`}>
                  {r.points}
                </td>
                <td className="hidden px-3 py-2 lg:table-cell">
                  <Form form={r.form} />
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function Legend({ leagueId, rows }: { leagueId: number; rows: StandingRow[] }) {
  const seen = new Map<string, Zone>();
  rows.forEach((r) => {
    const z = zoneFor(leagueId, r.position, rows.length);
    if (z && !seen.has(z.id)) seen.set(z.id, z);
  });
  if (seen.size === 0) return null;
  return (
    <ul className="flex flex-wrap gap-x-6 gap-y-2 text-xs text-muted" aria-label="Table colours">
      {[...seen.values()].map((z) => (
        <li key={z.id} className="flex items-center gap-2">
          <span aria-hidden="true" className={`h-2.5 w-2.5 rounded-full ${ZONE_BG[z.tone]}`} />
          {z.label}
        </li>
      ))}
    </ul>
  );
}

export default function StandingsBoard() {
  const [leagueId, setLeagueId] = useState(TABLE_LEAGUE_IDS[0]);
  const { standings, error } = useStandings(leagueId);
  const league = LEAGUES.find((l) => l.id === leagueId);
  const allRows = standings?.groups.flatMap((g) => g.rows) ?? [];

  return (
    <div className="space-y-8">
      <MockBanner />

      <div role="group" aria-label="Choose a league" className="-mx-5 flex gap-2 overflow-x-auto px-5 pb-1">
        {TABLE_LEAGUE_IDS.map((id) => {
          const l = LEAGUES.find((x) => x.id === id)!;
          return (
            <button key={id} onClick={() => setLeagueId(id)} aria-pressed={leagueId === id} className={pill(leagueId === id)}>
              <span className="flex items-center gap-2">
                <LeagueLogo league={l} size="sm" />
                {l.name}
              </span>
            </button>
          );
        })}
      </div>

      <div className="flex items-center justify-between gap-4">
        <h2 className="flex items-center gap-4 font-display text-4xl tracking-tight">
          {league && <LeagueLogo league={league} size="md" />}
          {league?.name}
        </h2>
        <span className="text-xs text-muted">
          {league?.country} · {league?.id === 2 ? "League phase" : "Current season"}
        </span>
      </div>

      {error && !standings && <StateMessage tone="error">Can&apos;t load this table. Try again in a moment.</StateMessage>}
      {!standings && !error && <StateMessage>Loading table…</StateMessage>}
      {standings && standings.groups.length === 0 && <StateMessage>No table for this league yet.</StateMessage>}

      {standings?.groups.map((g) => (
        <section key={g.name ?? "table"} className="space-y-4">
          {g.name && <h3 className="text-sm font-semibold uppercase tracking-widest text-muted">{g.name}</h3>}
          <Table leagueId={leagueId} group={g} />
        </section>
      ))}

      {standings && allRows.length > 0 && <Legend leagueId={leagueId} rows={standings.groups[0].rows} />}
    </div>
  );
}
