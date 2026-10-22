import { usingMockData } from "@/lib/api";

export function StateMessage({
  children,
  tone,
}: {
  children: React.ReactNode;
  tone?: "error";
}) {
  return (
    <p className={`py-6 text-center text-sm ${tone === "error" ? "text-live" : "text-muted"}`}>
      {children}
    </p>
  );
}

export function MockBanner() {
  if (!usingMockData) return null;
  return (
    <p className="text-xs text-muted">
      Demo data. Set <code className="font-mono">NEXT_PUBLIC_API_URL</code> to connect the backend.
    </p>
  );
}
