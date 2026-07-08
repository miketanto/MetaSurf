import type { CardLine } from "./decklist";

// Deck export formats. Card names are passed through verbatim from the user's
// list (we don't own a name→set-code map yet, so exports are name+count, which
// MTGA/MTGO both accept on import).

const main = (c: CardLine[]) => c.filter((x) => x.board !== "side");
const side = (c: CardLine[]) => c.filter((x) => x.board === "side");
const line = (c: CardLine) => `${c.count} ${c.name}`;

// MTGA: "Deck" / "Sideboard" headers, one "count name" per line.
export function toArena(cards: CardLine[]): string {
  const out = ["Deck", ...main(cards).map(line)];
  const sb = side(cards);
  if (sb.length) out.push("", "Sideboard", ...sb.map(line));
  return out.join("\n");
}

// MTGO .txt: mainboard, a blank line, then sideboard. No headers.
export function toMtgo(cards: CardLine[]): string {
  const out = main(cards).map(line);
  const sb = side(cards);
  if (sb.length) out.push("", ...sb.map(line));
  return out.join("\n");
}

// TCGplayer mass-entry cart: combine main+side, sum duplicate names, encode as
// `count name||count name`. NOTE: this is the widely-used massentry format but
// TCGplayer may change it — verify the built link opens a populated cart.
export function tcgplayerUrl(cards: CardLine[]): string {
  const totals = new Map<string, number>();
  for (const c of cards) totals.set(c.name, (totals.get(c.name) ?? 0) + c.count);
  const entries = [...totals.entries()].map(([name, n]) => `${n} ${name}`).join("||");
  return `https://www.tcgplayer.com/massentry?productline=Magic&c=${encodeURIComponent(entries)}`;
}
