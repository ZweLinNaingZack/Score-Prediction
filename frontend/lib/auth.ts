"use client";

import { useSyncExternalStore } from "react";

// Login state: the token lives in localStorage. A tiny external store lets every component
// (header, match page, match fetching) react to sign-in and sign-out without a provider.
const KEY = "scoreline.session";

export type Session = { token: string; email: string; name?: string };

// What to show for the user: their name, or the part of the email before the @ (older sessions).
export const displayName = (s: Session) => s.name || s.email.split("@")[0];

let cache: { raw: string | null; session: Session | null } = { raw: null, session: null };
const listeners = new Set<() => void>();

function read(): Session | null {
  try {
    const raw = localStorage.getItem(KEY);
    if (raw === cache.raw) return cache.session; // same reference until it changes
    cache = { raw, session: raw ? (JSON.parse(raw) as Session) : null };
  } catch {
    cache = { raw: null, session: null };
  }
  return cache.session;
}

function emit() {
  listeners.forEach((l) => l());
}

export function getSession(): Session | null {
  return read();
}

export function setSession(session: Session | null) {
  try {
    if (session) localStorage.setItem(KEY, JSON.stringify(session));
    else localStorage.removeItem(KEY);
  } catch {
    /* storage blocked: sign-in just will not persist */
  }
  emit();
}

function subscribe(cb: () => void) {
  listeners.add(cb);
  window.addEventListener("storage", cb); // other tabs
  return () => {
    listeners.delete(cb);
    window.removeEventListener("storage", cb);
  };
}

// Server render and first client render see "signed out", then the real session arrives.
export function useSession(): Session | null {
  return useSyncExternalStore(subscribe, read, () => null);
}
