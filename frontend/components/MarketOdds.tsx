import type { Chances, Match, Odds } from "@/lib/types";

const pct = (x: number) => Math.round(x * 100);

// Public: what the bookmakers' average odds say. No bookmaker names and no links on purpose.
export function MarketOdds({ match, odds }: { match: Match; odds: Odds }) {
  const tiles = [
    { label: match.home.name, short: match.home.short, odds: odds.home, chance: odds.chances.home },
    { label: "Draw", short: "Draw", odds: odds.draw, chance: odds.chances.draw },
    { label: match.away.name, short: match.away.short, odds: odds.away, chance: odds.chances.away },
  ];
  const favourite = Math.max(...tiles.map((t) => t.chance));

  return (
    <section aria-labelledby="odds-heading" className="space-y-4">
      <h2 id="odds-heading" className="font-display text-3xl tracking-tight">Market odds</h2>
      <ul className="grid grid-cols-3 gap-3">
        {tiles.map((t) => (
          <li
            key={t.label}
            className={`rounded-2xl border p-4 text-center ${
              t.chance === favourite ? "border-accent/50 bg-accent/[0.07]" : "border-line bg-surface"
            }`}
          >
            <div className="truncate text-xs uppercase tracking-widest text-muted">
              <span className="sm:hidden" title={t.label}>{t.short}</span>
              <span className="hidden sm:inline">{t.label}</span>
            </div>
            <div className="mt-1 font-display text-4xl tabular-nums leading-none">{t.odds.toFixed(2)}</div>
            <div className="mt-2 text-xs text-muted tabular-nums">{pct(t.chance)}% chance</div>
          </li>
        ))}
      </ul>
      <p className="text-xs text-muted">
        Average of {odds.bookmakers} bookmakers, margin removed from the chances. For comparison only, not
        betting advice. 18+.
      </p>
    </section>
  );
}

function Row({ label, market, model }: { label: string; market: number; model: number }) {
  const gap = pct(model) - pct(market);
  return (
    <li className="grid grid-cols-[4.5rem_1fr_3.5rem] items-center gap-3 text-sm sm:grid-cols-[6rem_1fr_4rem]">
      <span className="truncate text-muted">{label}</span>
      <span className="space-y-1.5">
        <span className="flex items-center gap-2">
          <span className="h-1.5 rounded-full bg-foreground/40" style={{ width: `${pct(market)}%` }} />
          <span className="text-xs tabular-nums text-muted">{pct(market)}%</span>
        </span>
        <span className="flex items-center gap-2">
          <span className="h-1.5 rounded-full bg-accent" style={{ width: `${pct(model)}%` }} />
          <span className="text-xs tabular-nums text-accent">{pct(model)}%</span>
        </span>
      </span>
      <span className={`text-right tabular-nums ${Math.abs(gap) >= 5 ? "font-semibold text-accent" : "text-muted"}`}>
        {gap > 0 ? `+${gap}` : gap}
        <span className="sr-only"> points versus the market</span>
      </span>
    </li>
  );
}

// Inside Unlock: our model's chances next to the market's.
export function MarketCompare({ match, odds, model }: { match: Match; odds: Odds; model: Chances }) {
  const rows = [
    { key: "home", label: match.home.name, market: odds.chances.home, model: model.home },
    { key: "draw", label: "Draw", market: odds.chances.draw, model: model.draw },
    { key: "away", label: match.away.name, market: odds.chances.away, model: model.away },
  ];
  const biggest = rows.reduce((a, b) => (Math.abs(b.model - b.market) > Math.abs(a.model - a.market) ? b : a));
  const gap = pct(biggest.model) - pct(biggest.market);
  const verdict =
    Math.abs(gap) < 4
      ? "Our model and the market agree on this one."
      : `Our model gives ${biggest.label} ${Math.abs(gap)} points ${gap > 0 ? "more" : "less"} chance than the market.`;

  return (
    <section aria-labelledby="compare-heading" className="rounded-2xl border border-line bg-surface p-5">
      <div className="flex items-center justify-between gap-4">
        <h3 id="compare-heading" className="text-sm font-semibold uppercase tracking-widest text-muted">
          Market vs our model
        </h3>
        <span className="flex items-center gap-4 text-xs text-muted">
          <span className="flex items-center gap-1.5">
            <span aria-hidden="true" className="h-2 w-2 rounded-full bg-foreground/40" />
            Market
          </span>
          <span className="flex items-center gap-1.5">
            <span aria-hidden="true" className="h-2 w-2 rounded-full bg-accent" />
            Model
          </span>
        </span>
      </div>
      <ul className="mt-5 space-y-4">
        {rows.map((r) => (
          <Row key={r.key} label={r.label} market={r.market} model={r.model} />
        ))}
      </ul>
      <p className="mt-5 border-t border-line pt-4 text-sm">{verdict}</p>
    </section>
  );
}
