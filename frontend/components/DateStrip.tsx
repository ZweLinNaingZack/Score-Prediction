"use client";

export type Day = { key: string; weekday: string; day: string; isToday: boolean; hasMatches: boolean };

// Local calendar date as YYYY-MM-DD (not UTC, so late kickoffs land on the viewer's day).
export const dayKey = (d: Date) => d.toLocaleDateString("en-CA");

export function buildDays(kickoffs: string[], back = 3, ahead = 9): Day[] {
  const withMatches = new Set(kickoffs.map((k) => dayKey(new Date(k))));
  const todayKey = dayKey(new Date());
  const days: Day[] = [];
  for (let i = -back; i <= ahead; i++) {
    const d = new Date();
    d.setDate(d.getDate() + i);
    const key = dayKey(d);
    days.push({
      key,
      weekday: d.toLocaleDateString([], { weekday: "short" }),
      day: d.toLocaleDateString([], { day: "numeric", month: "short" }),
      isToday: key === todayKey,
      hasMatches: withMatches.has(key),
    });
  }
  return days;
}

export default function DateStrip({
  days,
  selected,
  onSelect,
}: {
  days: Day[];
  selected: string;
  onSelect: (key: string) => void;
}) {
  return (
    <div role="group" aria-label="Pick a date" className="-mx-5 flex gap-2 overflow-x-auto px-5 pb-1">
      {days.map((d) => {
        const active = d.key === selected;
        return (
          <button
            key={d.key}
            onClick={() => onSelect(d.key)}
            aria-pressed={active}
            className={`flex min-h-11 min-w-16 shrink-0 flex-col items-center rounded-xl border px-3 py-2 text-center transition-colors ${
              active
                ? "border-accent bg-accent text-on-accent"
                : "border-line text-muted hover:text-foreground"
            }`}
          >
            <span className="text-[11px] uppercase tracking-widest">{d.isToday ? "Today" : d.weekday}</span>
            <span className="text-sm font-medium tabular-nums">{d.day}</span>
            <span
              aria-hidden="true"
              className={`mt-1 h-1 w-1 rounded-full ${d.hasMatches ? (active ? "bg-on-accent" : "bg-accent") : "bg-transparent"}`}
            />
            {d.hasMatches && <span className="sr-only">has matches</span>}
          </button>
        );
      })}
    </div>
  );
}
