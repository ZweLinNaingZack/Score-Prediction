"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const LINKS = [
  { href: "/matches", label: "Matches" },
  { href: "/table", label: "Table" },
  { href: "/leaderboard", label: "Track record" },
];

export default function NavLinks() {
  const pathname = usePathname();
  return (
    <div className="flex gap-1 text-sm">
      {LINKS.map((l) => {
        const active = pathname === l.href || pathname.startsWith(`${l.href}/`);
        return (
          <Link
            key={l.href}
            href={l.href}
            aria-current={active ? "page" : undefined}
            className={`flex min-h-11 items-center border-b-2 px-3 transition-colors ${
              active
                ? "border-accent text-foreground"
                : "border-transparent text-muted hover:text-foreground"
            }`}
          >
            {l.label}
          </Link>
        );
      })}
    </div>
  );
}
