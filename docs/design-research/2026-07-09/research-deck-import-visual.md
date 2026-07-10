# Research: Deck Import UX + Visual Decklist Views (2026-07-10)

Live-fetched/measured findings (caveats at end). Each: pattern → pit-wall translation.

## A. Deck import

### 1. Three-lane intake — paste / file / URL; paste primary
Melee: card search, file upload (.txt/.dec/.dek), paste ("most common formats"). Moxfield (official wiki): file, URL (Archidekt/TappedOut), paste (Arena). decklist.gg: URL import from MTGTop8/Goldfish/Moxfield/mtgdecks/Melee.
**Translation:** "DECK INTAKE" console with three channel keys — PASTE / FILE / LINK — PASTE pre-depressed; carbon textarea with blinking block cursor; LINK slot shows recognized-source stamps; DSEG live line counter.

### 2. Permissive line grammar
Goldfish (live) accepts `Name`, `3 Name`, `3x Name`; `#` and `//` comment lines ignored. decklist.gg accepts `4`/`4x`, rejects `4:` and `x4` suffix, filters metadata sections. Arena dialect: `2 Defiant Strike (WAR) 9`. Liberal in, strict out.
**Translation:** swallow all dialects silently; echo a normalized readback column beside the raw paste (`QTY × NAME`, DSEG quantities) — raw text visibly becomes instrument data.

### 3. Sideboard delimiting: four dialects, support all
(1) blank line (MTGO/Goldfish); (2) named headers case-insensitive ("Sideboard"/"SB", Arena's `Deck`/`Sideboard`/`Companion`); (3) `SB:` line prefix (Cockatrice); (4) Archidekt category-tag-after-name.
**Translation:** parse all four; VISUALIZE the split: draggable riso-orange gasket line between MAIN and SIDE zones with DSEG counts (60/15). If the split was heuristic (blank line), the separator pulses amber until user confirms — a "latched" press state.

### 4. Unresolved names → fault manifest; never auto-corrected, never silently dropped
Archidekt: imports what resolves + reports errors per line; misspellings block only their line; special chars (Æ/à) recurring failure class. Arena hard-fails per line. Nobody guesses spellings.
**Translation:** matches CLAUDE.md rule 3 exactly. "FAULT LOG" panel: unresolved lines in mono with blinking orange fault LEDs, DSEG fault count; per-line Scryfall fuzzy candidates as pressable thumbnail chips — resolving is a deliberate press; import commits with faults quarantined.

### 5. Quantity-prefixed autocomplete for manual entry
Melee: type "4 lightn" → pick from popover; section (main/side) is a pre-selected mode. Moxfield enforces format legality at add-time (Scryfall search syntax).
**Translation:** command-strip at console foot: `≫ 4 lightn` with thumbnail suggestions, parsed qty pre-lit in DSEG; MAIN/SIDE two-position switch; illegal adds refuse the press (button won't depress; orange plate: "BANNED — MODERN").

### 6. Staged validation gate: parse → resolve → legality → size
Melee: validation tool with per-board counts + human-readable errors + explicit "Convert" step; decklist.gg validates live.
**Translation:** "SCRUTINEERING" strip: four sequential lamps PARSE / RESOLVE / LEGAL / SIZE (hollow→solid blue, orange on fault); DSEG board counts vs format config; SUBMIT key stays raised until all lamps lit.

### 7. Save flow + reciprocal export
Untapped embeds the MTGA code in the URL; "Copy to MTGA" everywhere. Moxfield "Copy for MTGO" is the clean interchange; "Copy for MTGA" silently drops non-Arena cards (known trap). Melee auto-names from archetype. Goldfish visual has "Download Image".
**Translation:** post-import "REGISTRATION" card: name pre-filled from MetaSurf's OWN classifier (differentiator), format select, tag chips. Export rail: COPY TEXT / COPY MTGA / DOWNLOAD IMG press-keys with COPIED LED. If an export would drop cards, warn BEFORE copying with the casualty list.

## B. Visual decklist views

### 8. Goldfish "Visual View" poster (measured live)
`.deck-visual-pile` per unique card; copies absolutely positioned at exactly 30px vertical offsets (149×207 imgs) — buried copies show title bars, bottom copy full. Playmat rows grouped by role; banner with color pips, per-type counts, mana-curve histogram. NOT responsive (1213px fixed at 375vw) — a poster for the Download Image button.
**Translation:** MetaSurf "POSTER" mode: Scryfall normal scans stacked at 30–36px cadence on carbon mat, riso header band, DSEG type counts + curve cluster, EXPORT IMG key. Deliberately fixed-width, screenshot-perfect — the social artifact, not the working view.

### 9. Archidekt Stacks (measured live)
5-column masonry of category stacks; header plate per stack (name + Qty + $); 258×386 cards at 38px peek; stacking = distinct cards per category (not copies); toolbar: View-as / Group-by / Sort-by / price source; collapses to single column at 390px.
**Translation:** the working "GARAGE" view: tool-chest drawer columns, header plates with DSEG count+price, ~36px peeks; Group-by as a rotary selector (TYPE/CURVE/ROLE/TAG) with detents; mobile = single column with sticky drawer labels; tap springs the full card forward with a mechanical lift (translate+shadow, no fade).

### 10. Untapped MTGA view (verified live)
Deck-view toggle Classic/MTGA/Text. MTGA dialect: distinct cards stack with peeking strips; QUANTITY is a printed ×4 badge on the strip (no physical pile) — far denser. Lands = one card + ×20. Type tab-bar with counts + mini curve. Header instruments: WINRATE / MATCHES / AVG DURATION. "Share Deck Image".
**Translation:** closest product to Pit-Wall's soul. DEFAULT deck view = the ×N-badge dialect (denser, scan-faster): DSEG orange ×N on strip right edge; meta-share/matchup instruments in header. Three-position mode switch: POSTER / CONSOLE / TEXT.

### 11. Sideboard = separate rail
Goldfish: distinct `.deck-visual-playmat-sideboard` right rail, rotated vertical label, continuous strip cascade, visually subordinate. Always adjacent-but-architecturally-separate.
**Translation:** "PIT BOX" right rail (rotated label, riso-orange edge gasket, DSEG 15 at head); docks below main as a collapsible drawer on narrow. Future: sideboard-guide analytics light up in-arrows per matchup here.

### 12. CSV is collection-grade, separate lane
Goldfish documents 10 CSV dialects identified by header line, carrying printing-level data. Deck text ≠ collection CSV.
**Translation:** keep deck intake lean — no CSV on the paste box. Future "INVENTORY MANIFEST" console sniffs dialect from header and announces it on a stamped plate before committing.

## Caveats
- mtgdecks.net: Cloudflare 403 (direct + real headless Chromium) — nothing claimed about it; stacked-poster geometry grounded in Goldfish's measured view instead (owner's screenshot shows the same pattern).
- Moxfield: Cloudflare-walled; sourced from official moxfield-public GitHub wiki + third-party docs.
- TappedOut bulk entry behind login; `Sideboard`/`SB:` conventions search-verified (Cockatrice wiki).
- Screenshots in session scratchpad: goldfish-visual.png, archidekt-desktop.png, archidekt-deck.png (390px), untapped-deck.png.
