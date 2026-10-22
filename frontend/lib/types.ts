export type MatchStatus = "LIVE" | "UPCOMING" | "FINISHED";

export type ModelId = "ml" | "gpt" | "grok" | "gemini" | "claude";

export type Chances = { home: number; draw: number; away: number }; // each 0-1, summing to 1

// Market odds averaged over bookmakers: decimal odds and the chances they imply (margin removed).
export type Odds = { home: number; draw: number; away: number; chances: Chances; bookmakers: number };

export type Prediction = {
  model: ModelId;
  home: number;
  away: number;
  confidence: number; // 0-1
  reason?: string | null; // why this pick, shown after unlock
  chances?: Chances | null; // the model's own win/draw/away chances
};

export type Team = {
  name: string;
  short: string;
  crest?: string | null; // logo URL, falls back to `short` when missing
};

export type Match = {
  id: number;
  leagueId: number;
  status: MatchStatus;
  kickoff: string; // ISO date
  minute: number | null; // only while LIVE
  home: Team;
  away: Team;
  score: { home: number; away: number } | null;
  odds: Odds | null; // public market odds, when available
  unlocked: boolean; // true once the signed-in user unlocked this match
  predictionModels: ModelId[]; // who has predicted; `predictions` is empty until unlocked
  predictions: Prediction[];
};

export type LeaderboardEntry = {
  model: ModelId;
  played: number;
  exactScores: number;
  correctOutcomes: number;
};

export type StandingRow = {
  position: number;
  team: string;
  short: string;
  crest: string | null;
  played: number;
  won: number;
  draw: number;
  lost: number;
  goalsFor: number;
  goalsAgainst: number;
  goalDifference: number;
  points: number;
  form: string; // last five results, oldest first, e.g. "WWDLW"
};

export type StandingGroup = { name: string | null; rows: StandingRow[] };

export type Standings = { leagueId: number; groups: StandingGroup[] };
