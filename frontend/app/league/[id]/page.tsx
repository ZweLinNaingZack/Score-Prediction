import { notFound } from "next/navigation";

import LeagueLogo from "@/components/LeagueLogo";
import MatchesBoard from "@/components/MatchesBoard";
import { LEAGUES, leagueById } from "@/lib/leagues";

export function generateStaticParams() {
  return LEAGUES.map((l) => ({ id: String(l.id) }));
}

export default async function LeaguePage({ params }: PageProps<"/league/[id]">) {
  const { id } = await params;
  const league = leagueById(Number(id));
  if (!league) notFound();

  return (
    <div className="space-y-8">
      <div className="flex items-center gap-5">
        <LeagueLogo league={league} size="lg" />
        <div>
          <p className="text-xs uppercase tracking-widest text-muted">{league.category}</p>
          <h1 className="mt-1 font-display text-5xl tracking-tight sm:text-6xl">{league.name}</h1>
          <p className="mt-1 text-sm text-muted">{league.country}</p>
        </div>
      </div>
      <MatchesBoard fixedLeagueId={league.id} />
    </div>
  );
}
