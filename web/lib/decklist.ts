// Parse a pasted decklist into {name, count, board} lines for /classify.
// Handles MTGO/Arena/Moxfield-ish formats: "4 Card", "4x Card", a "Sideboard"
// header, Arena set suffixes "(SET) 123", and // # comments. Card names are
// sent verbatim — the API resolves them and reports anything unknown; we never
// guess a spelling here.

export interface CardLine {
  name: string;
  count: number;
  board: string;
}

const SIDE_HEADER = /^(sideboard|sb)\b/i;
const MAIN_HEADER = /^(deck|mainboard|maindeck|commander|companion)\b[: ]*$/i;
const ARENA_SUFFIX = /\s+\([A-Za-z0-9]{2,5}\)\s+\d+\s*$/;
const COUNTED = /^(\d+)\s*[xX]?\s+(.+)$/;

export function parseDecklist(text: string): CardLine[] {
  const out: CardLine[] = [];
  let board = "main";
  for (const raw of text.split(/\r?\n/)) {
    const line = raw.trim();
    if (!line || line.startsWith("//") || line.startsWith("#")) continue;
    if (SIDE_HEADER.test(line)) {
      board = "side";
      continue;
    }
    if (MAIN_HEADER.test(line)) {
      board = "main";
      continue;
    }
    const m = COUNTED.exec(line);
    const count = m ? parseInt(m[1], 10) : 1;
    let name = (m ? m[2] : line).replace(ARENA_SUFFIX, "").trim();
    // split-card and DFC normalisation is the API's job; send the printed name
    if (!name) continue;
    out.push({ name, count, board });
  }
  return out;
}
