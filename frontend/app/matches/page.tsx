import MatchesBoard from "@/components/MatchesBoard";

export const metadata = { title: "Matches · Score Prediction" };

export default function MatchesPage() {
  return (
    <div className="space-y-8">
      <h1 className="font-display text-6xl tracking-tight">Matches</h1>
      <MatchesBoard />
    </div>
  );
}
