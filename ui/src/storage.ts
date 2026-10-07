import type { Revision } from "./types";

const REVISIONS_KEY = "docextract.revisions";

function readJson<T>(key: string, fallback: T): T {
  if (typeof window === "undefined") return fallback;
  try {
    const raw = window.localStorage.getItem(key);
    return raw ? (JSON.parse(raw) as T) : fallback;
  } catch {
    return fallback;
  }
}

export function loadRevisions(): Record<string, Revision[]> {
  return readJson(REVISIONS_KEY, {});
}

export function saveRevisions(revisions: Record<string, Revision[]>): void {
  window.localStorage.setItem(REVISIONS_KEY, JSON.stringify(revisions));
}
