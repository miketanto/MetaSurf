import type { DeckCard } from "./types";

// Group mainboard cards by their primary type for the mtgdecks-style deck
// view. Front-face type wins for DFCs ("Creature — X // Land").
const ORDER = [
  "Creature",
  "Planeswalker",
  "Instant",
  "Sorcery",
  "Enchantment",
  "Artifact",
  "Battle",
  "Land",
  "Other",
] as const;

export function primaryType(typeLine: string | null): string {
  const front = (typeLine ?? "").split("//")[0];
  for (const t of ORDER) {
    if (t !== "Other" && front.includes(t)) {
      // Artifact Creatures count as creatures; enchantment creatures too
      if (t === "Enchantment" && front.includes("Creature")) return "Creature";
      if (t === "Artifact" && front.includes("Creature")) return "Creature";
      return t;
    }
  }
  return "Other";
}

export function groupByType(cards: DeckCard[]): [string, DeckCard[]][] {
  const groups = new Map<string, DeckCard[]>();
  for (const c of cards) {
    const t = primaryType(c.type_line);
    (groups.get(t) ?? groups.set(t, []).get(t)!).push(c);
  }
  const out: [string, DeckCard[]][] = [];
  for (const t of ORDER) {
    const g = groups.get(t);
    if (g && g.length) {
      g.sort((a, b) => (b.count - a.count) || a.name.localeCompare(b.name));
      out.push([t, g]);
    }
  }
  return out;
}

export function countOf(cards: DeckCard[]): number {
  return cards.reduce((s, c) => s + c.count, 0);
}
