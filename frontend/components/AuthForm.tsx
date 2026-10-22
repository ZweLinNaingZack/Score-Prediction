"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { signIn } from "@/lib/api";

const input =
  "min-h-11 w-full rounded-xl border border-line bg-surface px-4 text-base text-foreground placeholder:text-muted focus:border-accent";

// Same rules as the server (backend/app/auth.py password_problem), checked here for a quicker answer.
const RULES: { label: string; ok: (p: string) => boolean }[] = [
  { label: "8 or more characters", ok: (p) => p.length >= 8 },
  { label: "a lowercase letter", ok: (p) => /[a-z]/.test(p) },
  { label: "a capital letter", ok: (p) => /[A-Z]/.test(p) },
  { label: "a number", ok: (p) => /[0-9]/.test(p) },
  { label: "a symbol, like ! or #", ok: (p) => /[^A-Za-z0-9]/.test(p) },
];

export default function AuthForm() {
  const router = useRouter();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [password, setPassword] = useState("");

  async function onSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = new FormData(e.currentTarget);
    if (mode === "register" && RULES.some((r) => !r.ok(password))) {
      setError("Your password does not meet all the rules below.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await signIn(
        mode,
        String(form.get("email")),
        String(form.get("password")),
        String(form.get("name") ?? "").trim(),
      );
      // go back to the match the user came from, or to the match list
      if (document.referrer.startsWith(window.location.origin) && !document.referrer.endsWith("/login")) router.back();
      else router.push("/matches");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong. Try again.");
      setBusy(false);
    }
  }

  const registering = mode === "register";

  return (
    <form onSubmit={onSubmit} className="mx-auto w-full max-w-sm space-y-5">
      <div>
        <h1 className="font-display text-5xl tracking-tight">{registering ? "Create account" : "Sign in"}</h1>
        <p className="mt-2 text-sm text-muted">
          {registering ? "A free account unlocks match predictions." : "Sign in to unlock match predictions."}
        </p>
      </div>

      {registering && (
        <div className="space-y-2">
          <label htmlFor="name" className="text-sm text-muted">Name</label>
          <input
            id="name"
            name="name"
            type="text"
            required
            minLength={2}
            maxLength={40}
            autoComplete="name"
            placeholder="How should we call you?"
            className={input}
          />
        </div>
      )}
      <div className="space-y-2">
        <label htmlFor="email" className="text-sm text-muted">Email</label>
        <input id="email" name="email" type="email" required autoComplete="email" className={input} />
      </div>
      <div className="space-y-2">
        <label htmlFor="password" className="text-sm text-muted">Password</label>
        <input
          id="password"
          name="password"
          type="password"
          required
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          aria-describedby={registering ? "password-rules" : undefined}
          autoComplete={registering ? "new-password" : "current-password"}
          className={input}
        />
        {registering && (
          <ul id="password-rules" className="space-y-1 text-xs">
            {RULES.map((r) => {
              const ok = r.ok(password);
              return (
                <li key={r.label} className={ok ? "text-accent" : "text-muted"}>
                  <span aria-hidden="true">{ok ? "✓" : "○"}</span> {r.label}
                  <span className="sr-only">{ok ? " (done)" : " (needed)"}</span>
                </li>
              );
            })}
          </ul>
        )}
      </div>

      {error && (
        <p role="alert" className="text-sm text-live">
          {error}
        </p>
      )}

      <button
        type="submit"
        disabled={busy}
        className="min-h-11 w-full rounded-full bg-accent font-semibold text-on-accent transition-opacity disabled:opacity-60"
      >
        {busy ? "Please wait…" : registering ? "Create account" : "Sign in"}
      </button>

      <button
        type="button"
        onClick={() => {
          setMode(registering ? "login" : "register");
          setError(null);
          setPassword("");
        }}
        className="min-h-11 w-full text-sm text-muted transition-colors hover:text-foreground"
      >
        {registering ? "Already have an account? Sign in" : "New here? Create an account"}
      </button>
    </form>
  );
}
