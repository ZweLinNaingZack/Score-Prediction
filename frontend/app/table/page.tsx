import StandingsBoard from "@/components/StandingsBoard";

export const metadata = { title: "League tables · Score Prediction" };

export default function TablePage() {
  return (
    <div className="space-y-8">
      <div>
        <p className="text-xs uppercase tracking-widest text-muted">Standings</p>
        <h1 className="mt-1 font-display text-6xl tracking-tight">League tables</h1>
        <p className="mt-2 max-w-xl text-muted">Live positions in Europe&apos;s top five leagues and the Champions League.</p>
      </div>
      <StandingsBoard />
    </div>
  );
}
