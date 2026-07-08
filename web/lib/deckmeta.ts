import type { DeckSummary } from "./types";

export function record(d: DeckSummary): string {
  if (d.wins != null && d.losses != null) return `${d.wins}–${d.losses}`;
  if (d.finish_rank != null) return `#${d.finish_rank}`;
  return "";
}

// A short "notable finish" badge, or "" if unremarkable.
export function finishBadge(d: DeckSummary): string {
  if (d.wins != null && d.losses === 0 && d.wins >= 4) return `${d.wins}-0`;
  if (d.finish_rank === 1) return "1st";
  if (d.finish_rank != null && d.finish_rank <= 8) return `Top 8`;
  if (d.finish_rank != null && d.finish_rank <= 16) return `Top 16`;
  return "";
}

// Notable = an undefeated league run or a Top-8 tournament finish.
export function isNotable(d: DeckSummary): boolean {
  if (d.wins != null && d.losses === 0 && d.wins >= 4) return true;
  return d.finish_rank != null && d.finish_rank <= 8;
}

export function winPct(d: DeckSummary): number {
  if (d.wins != null && d.losses != null && d.wins + d.losses > 0) {
    return d.wins / (d.wins + d.losses);
  }
  return -1; // unknown record sorts last
}
