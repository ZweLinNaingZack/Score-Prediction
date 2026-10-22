import MatchDetail from "@/components/MatchDetail";

export const metadata = { title: "Match · Score Prediction" };

// Real ids are only known at runtime. One placeholder lets the build prerender the shell;
// other ids render on first visit.
export function generateStaticParams() {
  return [{ id: "0" }];
}

export default async function MatchPage({ params }: PageProps<"/match/[id]">) {
  const { id } = await params;
  return <MatchDetail id={Number(id)} />;
}
