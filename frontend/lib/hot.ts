import type { Match } from "./types";

// Rough prestige weight per league id; higher means a bigger draw.
const LEAGUE_WEIGHT: Record<number, number> = {
  2: 5,
  39: 4.5,
  140: 4.2,
  135: 3.6,
  78: 3.6,
  3: 3.2,
  61: 3,
  5: 2.8,
};

const weight = (m: Match) => LEAGUE_WEIGHT[m.leagueId] ?? 2;

function liveHeat(m: Match) {
  const home = m.score?.home ?? 0;
  const away = m.score?.away ?? 0;
  const close = Math.abs(home - away) <= 1 ? 5 : 0;
  const late = (m.minute ?? 0) >= 75 ? 4 : 0;
  return weight(m) * 10 + (home + away) * 4 + close + late;
}

function upcomingHeat(m: Match, now: number) {
  const hours = (new Date(m.kickoff).getTime() - now) / 3_600_000;
  return weight(m) * 10 + Math.max(0, 48 - hours) * 0.5;
}

export function hottestLive(matches: Match[], n = 5) {
  return matches
    .filter((m) => m.status === "LIVE")
    .sort((a, b) => liveHeat(b) - liveHeat(a))
    .slice(0, n);
}

export function hottestUpcoming(matches: Match[], n = 5, now = Date.now()) {
  return matches
    .filter((m) => m.status === "UPCOMING")
    .sort((a, b) => upcomingHeat(b, now) - upcomingHeat(a, now))
    .slice(0, n);
}
