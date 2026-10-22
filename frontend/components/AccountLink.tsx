"use client";

import Link from "next/link";

import { displayName, setSession, useSession } from "@/lib/auth";

const item = "flex min-h-11 items-center whitespace-nowrap px-3 text-sm transition-colors";

// Header control: "Sign in" when signed out, "Sign out" (with the email on wide screens) when in.
export default function AccountLink() {
  const session = useSession();

  if (!session) {
    return (
      <Link href="/login" className={`${item} font-medium text-accent hover:text-foreground`}>
        Sign in
      </Link>
    );
  }
  return (
    <button
      onClick={() => setSession(null)}
      className={`${item} text-muted hover:text-foreground`}
      aria-label={`Sign out ${displayName(session)}`}
    >
      <span className="mr-2 hidden max-w-40 truncate text-xs sm:inline">{displayName(session)}</span>
      Sign out
    </button>
  );
}
