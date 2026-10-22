import Link from "next/link";

import AccountLink from "./AccountLink";
import NavLinks from "./NavLinks";

// Phone: logo and account on the first row, page links on a second row. Wide: one row.
export default function Header() {
  return (
    <header className="sticky top-0 z-20 border-b border-line bg-background/85 backdrop-blur">
      <nav
        aria-label="Primary"
        className="mx-auto flex max-w-6xl flex-wrap items-center justify-between px-5 sm:flex-nowrap"
      >
        <Link href="/" className="flex min-h-15 items-center font-display text-3xl tracking-wide">
          SCORELINE<span className="text-accent">.</span>
        </Link>
        <div className="order-3 -mx-3 flex w-full sm:order-2 sm:mx-0 sm:ml-auto sm:w-auto">
          <NavLinks />
        </div>
        <div className="order-2 sm:order-3">
          <AccountLink />
        </div>
      </nav>
    </header>
  );
}
