import type { MatchupCell, MatchupsResponse } from "./types";

export const pctInt = (p: number) => Math.round(p * 100);

// Diverging tint: red when unfavoured, green when favoured, ~transparent at 50%.
// Full saturation by the time the edge is 25 points off even.
export function tint(p: number): string {
  const strength = Math.min(1, Math.abs(p - 0.5) / 0.25);
  const alpha = (0.1 + 0.5 * strength).toFixed(3);
  return p >= 0.5
    ? `rgba(70, 195, 154, ${alpha})` // --good
    : `rgba(229, 100, 110, ${alpha})`; // --bad
}

export type Confidence = "high" | "med" | "low";

// Sample-size → confidence bucket. Wide CIs on tiny n are the honest caveat;
// the UI fades low-confidence cells and shows a dot in the breakdown.
export function confidence(n: number): Confidence {
  if (n >= 100) return "high";
  if (n >= 30) return "med";
  return "low";
}

export const confidenceOpacity: Record<Confidence, number> = {
  high: 1,
  med: 0.82,
  low: 0.4,
};

// A short header code from an archetype name, e.g. "GenericMidrange" -> "GMi",
// "Aggro" -> "Agg". Uppercase word-initials, padded from the first word.
export function code(name: string): string {
  const words = name.split(/[\s-]+/).filter(Boolean);
  if (words.length >= 2) {
    return (words[0][0] + words[1][0] + (words[1][1] ?? "")).toUpperCase().slice(0, 3);
  }
  return name.slice(0, 3).toUpperCase();
}

export function cellIndex(m: MatchupsResponse): Map<string, MatchupCell> {
  const idx = new Map<string, MatchupCell>();
  for (const c of m.cells) idx.set(`${c.arch_a}:${c.arch_b}`, c);
  return idx;
}
