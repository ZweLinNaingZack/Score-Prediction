import { MODELS } from "./leagues";
import type { LeaderboardEntry, Match, MatchStatus, Prediction, Standings, Team } from "./types";

const t = (name: string, short: string): Team => ({ name, short });

// [leagueId, home, away, status, minutes-from-now offset (kickoff), current score]
type Seed = [number, Team, Team, MatchStatus, number, [number, number]?];

const SEEDS: Seed[] = [
  [39, t("Arsenal", "ARS"), t("Chelsea", "CHE"), "LIVE", -34, [1, 0]],
  [39, t("Liverpool", "LIV"), t("Man City", "MCI"), "UPCOMING", 180],
  [39, t("Tottenham", "TOT"), t("Newcastle", "NEW"), "UPCOMING", 1500],
  [39, t("Aston Villa", "AVL"), t("Brighton", "BHA"), "FINISHED", -1440, [2, 2]],
  [140, t("Real Madrid", "RMA"), t("Barcelona", "BAR"), "LIVE", -71, [2, 2]],
  [140, t("Atletico Madrid", "ATM"), t("Sevilla", "SEV"), "UPCOMING", 240],
  [135, t("Inter", "INT"), t("Juventus", "JUV"), "UPCOMING", 360],
  [135, t("Napoli", "NAP"), t("AC Milan", "MIL"), "FINISHED", -1500, [1, 0]],
  [78, t("Bayern Munich", "BAY"), t("Dortmund", "BVB"), "UPCOMING", 420],
  [61, t("PSG", "PSG"), t("Marseille", "MAR"), "UPCOMING", 600],
  [2, t("Bayern Munich", "BAY"), t("Inter", "INT"), "UPCOMING", 2900],
  [2, t("Real Madrid", "RMA"), t("PSG", "PSG"), "LIVE", -12, [0, 0]],
  [3, t("Roma", "ROM"), t("Tottenham", "TOT"), "UPCOMING", 2950],
  [5, t("England", "ENG"), t("Spain", "ESP"), "UPCOMING", 4300],
  [5, t("France", "FRA"), t("Germany", "GER"), "FINISHED", -2880, [2, 1]],
  [78, t("Leipzig", "RBL"), t("Leverkusen", "B04"), "LIVE", -63, [1, 1]],
  [135, t("Roma", "ROM"), t("Lazio", "LAZ"), "LIVE", -80, [2, 1]],
];

// small deterministic hash so mock predictions stay stable between renders
const hash = (n: number) => {
  const x = Math.sin(n * 9301 + 49297) * 233280;
  return x - Math.floor(x);
};

function predictionsFor(matchId: number): Prediction[] {
  return MODELS.map((m, i) => ({
    model: m.id,
    home: Math.floor(hash(matchId * 10 + i) * 4),
    away: Math.floor(hash(matchId * 10 + i + 50) * 3),
    confidence: 0.4 + hash(matchId * 10 + i + 99) * 0.5,
    reason: "Demo reason: recent form and home advantage point to this scoreline.",
    chances: { home: 0.5, draw: 0.26, away: 0.24 },
  }));
}

export function getMockMatches(now = Date.now()): Match[] {
  return SEEDS.map(([leagueId, home, away, status, offsetMin, score], idx) => ({
    id: idx + 1,
    leagueId,
    status,
    kickoff: new Date(now + offsetMin * 60_000).toISOString(),
    minute: status === "LIVE" ? Math.min(90, -offsetMin) : null,
    home,
    away,
    score: score ? { home: score[0], away: score[1] } : null,
    odds:
      status === "FINISHED"
        ? null
        : { home: 2.0, draw: 3.5, away: 3.8, chances: { home: 0.46, draw: 0.27, away: 0.27 }, bookmakers: 12 },
    unlocked: false,
    predictionModels: MODELS.map((m) => m.id),
    predictions: predictionsFor(idx + 1), // demo only: the real API withholds these until unlocked
  }));
}

export function getMockLeaderboard(): LeaderboardEntry[] {
  return MODELS.map((m, i) => {
    const played = 40;
    return {
      model: m.id,
      played,
      exactScores: 5 + Math.floor(hash(i + 1) * 8),
      correctOutcomes: 16 + Math.floor(hash(i + 7) * 12),
    };
  });
}

const MOCK_TEAMS: [string, string][] = [
  ["Man City", "MCI"], ["Arsenal", "ARS"], ["Brighton", "BHA"], ["Liverpool", "LIV"],
  ["Chelsea", "CHE"], ["Tottenham", "TOT"], ["Newcastle", "NEW"], ["Aston Villa", "AVL"],
];

// Demo table (no backend): the same eight teams for every league.
export function getMockStandings(leagueId: number): Standings {
  return {
    leagueId,
    groups: [
      {
        name: null,
        rows: MOCK_TEAMS.map(([team, short], i) => ({
          position: i + 1, team, short, crest: null, played: 7, won: 6 - Math.floor(i / 2), draw: 1, lost: Math.floor(i / 2),
          goalsFor: 18 - i * 2, goalsAgainst: 6 + i, goalDifference: 12 - i * 3, points: 19 - i * 2,
          form: ["WWLWW", "LWWWD", "DWWWW", "WDWLW", "WWDLL", "LDWWL", "DLWDL", "LLDWL"][i],
        })),
      },
    ],
  };
}
