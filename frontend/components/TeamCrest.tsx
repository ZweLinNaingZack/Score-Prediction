"use client";

import { useState } from "react";

import type { Team } from "@/lib/types";

type Size = "sm" | "md" | "lg" | "xl";

const BOX: Record<Size, string> = {
  sm: "h-8 w-8 text-xs",
  md: "h-12 w-12 text-xl",
  lg: "h-16 w-16 text-2xl",
  xl: "h-24 w-24 text-4xl sm:h-32 sm:w-32",
};

// Team logo. Falls back to the 3-letter code if there is no logo or it fails to load.
export default function TeamCrest({
  team,
  large,
  size = large ? "lg" : "md",
}: {
  team: Team;
  large?: boolean;
  size?: Size;
}) {
  const [failed, setFailed] = useState(false);
  const box = BOX[size];

  if (team.crest && !failed) {
    return (
      // eslint-disable-next-line @next/next/no-img-element -- crests are small remote SVG/PNG files
      <img
        src={team.crest}
        alt=""
        loading="lazy"
        onError={() => setFailed(true)}
        className={`shrink-0 object-contain ${box.split(" ").slice(0, 2).join(" ")}`}
      />
    );
  }
  return (
    <span
      aria-hidden="true"
      className={`flex shrink-0 items-center justify-center rounded-full border border-line bg-surface font-display tracking-wider ${box}`}
    >
      {team.short}
    </span>
  );
}
