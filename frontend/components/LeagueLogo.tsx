"use client";

import { useState } from "react";

import type { League } from "@/lib/leagues";

const SIZE = {
  sm: { box: "h-8 w-8 rounded-lg p-1", text: "text-xs" },
  md: { box: "h-12 w-12 rounded-xl p-1.5", text: "text-base" },
  lg: { box: "h-16 w-16 rounded-2xl p-2", text: "text-xl" },
};

// League logo on a light plate (most logos are dark and would vanish on black).
// Falls back to the short code when there is no logo or it fails to load.
export default function LeagueLogo({ league, size = "md" }: { league: League; size?: keyof typeof SIZE }) {
  const [failed, setFailed] = useState(false);
  const s = SIZE[size];

  if (league.logo && !failed) {
    return (
      <span className={`flex shrink-0 items-center justify-center bg-white ${s.box}`}>
        {/* eslint-disable-next-line @next/next/no-img-element -- small remote PNG */}
        <img
          src={league.logo}
          alt=""
          onError={() => setFailed(true)}
          className="h-full w-full object-contain"
        />
      </span>
    );
  }
  return (
    <span
      aria-hidden="true"
      className={`flex shrink-0 items-center justify-center border border-line bg-surface font-display tracking-wide text-muted ${s.box} ${s.text}`}
    >
      {league.short}
    </span>
  );
}
