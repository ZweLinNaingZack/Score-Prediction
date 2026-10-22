import Leaderboard from "@/components/Leaderboard";

export const metadata = { title: "Track record · Score Prediction" };

export default function LeaderboardPage() {
  return (
    <div className="space-y-8">
      <div>
        <h1 className="font-display text-6xl tracking-tight">Track record</h1>
        <p className="mt-1 text-sm text-muted">
          How the model has done on finished matches it predicted before kickoff.
        </p>
      </div>
      <Leaderboard />
    </div>
  );
}
