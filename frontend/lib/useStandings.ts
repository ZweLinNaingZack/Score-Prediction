"use client";

import { useEffect, useState } from "react";

import { fetchStandings } from "./api";
import type { Standings } from "./types";

const REFRESH_MS = 5 * 60_000;

// Loads one league's table and keeps the others cached, so switching tabs back is instant.
export function useStandings(leagueId: number) {
  const [store, setStore] = useState<Record<number, Standings>>({});
  const [failed, setFailed] = useState<Record<number, boolean>>({});

  useEffect(() => {
    let cancelled = false;
    const load = () =>
      fetchStandings(leagueId)
        .then((s) => {
          if (cancelled) return;
          setStore((prev) => ({ ...prev, [leagueId]: s }));
          setFailed((prev) => ({ ...prev, [leagueId]: false }));
        })
        .catch(() => !cancelled && setFailed((prev) => ({ ...prev, [leagueId]: true })));
    load();
    const timer = setInterval(load, REFRESH_MS);
    return () => {
      cancelled = true;
      clearInterval(timer);
    };
  }, [leagueId]);

  return { standings: store[leagueId] ?? null, error: !!failed[leagueId] };
}
