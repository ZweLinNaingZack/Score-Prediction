import { getSession, setSession } from "./auth";
import { getMockLeaderboard, getMockMatches, getMockStandings } from "./mock";
import type { LeaderboardEntry, Match, Standings } from "./types";

// Set NEXT_PUBLIC_API_URL (e.g. http://127.0.0.1:8000/api) once the backend serves
// /matches and /leaderboard. Until then the app runs on mock data.
const API_URL = process.env.NEXT_PUBLIC_API_URL;

export const usingMockData = !API_URL;

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
  ) {
    super(message);
  }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const token = getSession()?.token;
  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    cache: "no-store",
    headers: {
      ...(init.body ? { "Content-Type": "application/json" } : {}),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
  });
  if (res.status === 401 && token) setSession(null); // expired or invalid token
  if (!res.ok) {
    let detail = `API ${path} failed: ${res.status}`;
    try {
      const body = await res.json();
      if (typeof body.detail === "string") detail = body.detail;
    } catch {
      /* keep the generic message */
    }
    throw new ApiError(detail, res.status);
  }
  return res.json();
}

export async function fetchMatches(): Promise<Match[]> {
  return API_URL ? request<Match[]>("/matches") : getMockMatches();
}

export async function fetchLeaderboard(): Promise<LeaderboardEntry[]> {
  return API_URL ? request<LeaderboardEntry[]>("/leaderboard") : getMockLeaderboard();
}

export async function fetchStandings(leagueId: number): Promise<Standings> {
  return API_URL ? request<Standings>(`/standings/${leagueId}`) : getMockStandings(leagueId);
}

export async function signIn(mode: "login" | "register", email: string, password: string, name?: string) {
  const out = await request<{ token: string; email: string; name: string }>(`/auth/${mode}`, {
    method: "POST",
    body: JSON.stringify(mode === "register" ? { email, password, name } : { email, password }),
  });
  setSession({ token: out.token, email: out.email, name: out.name });
}

export async function unlockMatch(matchId: number) {
  await request(`/matches/${matchId}/unlock`, { method: "POST" });
}
