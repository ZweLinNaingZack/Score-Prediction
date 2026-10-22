"use client";

import { useCallback, useEffect, useState } from "react";

import { fetchMatches } from "./api";
import { useSession } from "./auth";
import type { Match } from "./types";

const REFRESH_MS = 30_000;

// Loads matches and re-fetches every 30s so live scores stay fresh. Also re-fetches when the user
// signs in or out, because unlocked predictions depend on who is asking.
export function useMatches() {
  const [matches, setMatches] = useState<Match[] | null>(null);
  const [error, setError] = useState(false);
  const session = useSession();
  const token = session?.token ?? null;
  const [tick, setTick] = useState(0);
  const reload = useCallback(() => setTick((t) => t + 1), []);

  useEffect(() => {
    let cancelled = false;
    const load = () =>
      fetchMatches()
        .then((m) => {
          if (cancelled) return;
          setMatches(m);
          setError(false);
        })
        .catch(() => !cancelled && setError(true));
    load();
    const timer = setInterval(load, REFRESH_MS);
    return () => {
      cancelled = true;
      clearInterval(timer);
    };
  }, [token, tick]);

  return { matches, error, refreshSeconds: REFRESH_MS / 1000, reload };
}
