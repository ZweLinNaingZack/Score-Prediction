import type { ModelId } from "./types";

// ids are API-Football league ids
export type League = {
  id: number;
  name: string;
  short: string;
  country: string;
  category: "Domestic league" | "European" | "International";
  logo?: string; // football-data.org emblem; none for the Nations League
};

export const LEAGUES: League[] = [
  { id: 39, name: "Premier League", short: "PL", country: "England", category: "Domestic league", logo: 'https://crests.football-data.org/PL.png' },
  { id: 140, name: "La Liga", short: "LL", country: "Spain", category: "Domestic league", logo: 'https://crests.football-data.org/laliga.png' },
  { id: 135, name: "Serie A", short: "SA", country: "Italy", category: "Domestic league", logo: 'https://crests.football-data.org/c111.png' },
  { id: 78, name: "Bundesliga", short: "BL", country: "Germany", category: "Domestic league", logo: 'https://crests.football-data.org/BL1.png' },
  { id: 61, name: "Ligue 1", short: "L1", country: "France", category: "Domestic league", logo: 'https://crests.football-data.org/FL1.png' },
  { id: 2, name: "UEFA Champions League", short: "UCL", country: "Europe", category: "European", logo: 'https://crests.football-data.org/CL.png' },
  { id: 3, name: "UEFA Europa League", short: "UEL", country: "Europe", category: "European", logo: 'https://crests.football-data.org/EL.png' },
  { id: 5, name: "UEFA Nations League", short: "UNL", country: "Europe", category: "International" },
];

export const DEFAULT_LEAGUE_ID = 39;

export const leagueById = (id: number) => LEAGUES.find((l) => l.id === id);

export const MODELS: { id: ModelId; label: string }[] = [
  { id: "ml", label: "My model" },
];

export const modelLabel = (id: ModelId) => MODELS.find((m) => m.id === id)?.label ?? id;

// Leagues with a table (football-data.org free tier). Europa League and Nations League have none.
export const TABLE_LEAGUE_IDS = [39, 140, 135, 78, 61, 2];

export type Zone = { id: string; label: string; tone: "gold" | "light" | "down" | "warn" };

// Colour bands in the table. Domestic: top 4 and the relegation places. Champions League league phase:
// 1-8 straight to the last 16, 9-24 play-offs, 25+ out.
export function zoneFor(leagueId: number, position: number, total: number): Zone | null {
  if (leagueId === 2) {
    if (position <= 8) return { id: "last16", label: "Last 16", tone: "gold" };
    if (position <= 24) return { id: "playoff", label: "Play-offs", tone: "light" };
    return { id: "out", label: "Eliminated", tone: "down" };
  }
  if (position <= 4) return { id: "top4", label: "Top 4", tone: "gold" };
  const direct = leagueId === 78 || leagueId === 61 ? 2 : 3; // Bundesliga and Ligue 1 also have a 16th-place play-off
  if (position > total - direct) return { id: "relegation", label: "Relegation", tone: "down" };
  if (direct === 2 && position === total - 2) return { id: "rplayoff", label: "Relegation play-off", tone: "warn" };
  return null;
}
