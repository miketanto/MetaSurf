# PIT-WALL CONSOLE — ATTENTION & ART-ANCHOR SPEC (focal hierarchy, density budgets, card-art system)

**Status:** v1 draft for owner review, 2026-07-10.
**Base system:** `pit-wall-tokens.md` (cited as **tokens §n**) and `extension-spec.md`
(cited as **ext §n**). Nothing here overrides those specs; this spec adds the missing
layer between them: WHERE the eye goes first, HOW loud each instrument may be, and
WHERE card art anchors a page.

**Owner feedback driving this spec (2026-07-10):** "I think we need to introduce more
of the card arts and images into the design. There's a problem of where I should draw
my attention — when I open some of the pages I feel overwhelmed."

**Evidence base:** every count below was taken 2026-07-10 by reading the markup of the
14 mockups in this directory (4 v3 pages in `pit-wall-console/` + 10 wave-2 pages),
counting elements in the first ~900px of mobile DOM order (ticker + header + the first
2–3 sections — the 390×844 first viewport). "DSEG readout" = one value set in
`DSEG7Classic`; "chip" = one Press Start 2P chip/badge/button. No number in this
document is estimated; each is a count from a named file.

---

## 0. Diagnosis — what the liked pages do that the dense pages don't

### 0.1 The liked pages (owner-approved)

**`pit-wall-console/s-deck-viewer.html`** — first viewport at 390px: ticker → back
button + clock → **the duotone art band** (Snapcaster `img_art_crop`, ≥168px tall,
tint + grain + scrim, 42px Archivo title, 3 chips) → one dim event line → the DSEG
tile grid. Counts above the fold: **6 DSEG readouts incl. the clock** (clock, WR,
share, main, side, price edge), **4 chips** (back + 1ST PLACE + MODERN + AZJA),
**1 ticker**, **one image**. The band is the largest element, first in reading order,
and the only pictorial element on screen — the eye lands, then descends.

**`pit-wall-console/s3-archetype-detail.html`** — first viewport: ticker → back +
clock → 40px title + 3 chips + grainband → **one 2×2 DSEG grid (4 tiles)** + a dim
caption → the staples gallery begins (a single ~300×418px card scan — the fold-2
set-piece). Counts above the fold: **5 DSEG readouts incl. clock**, **4 chips**,
**1 ticker**. Everything between the loud moments is dim 9–10px caption text.

What makes them readable, concretely:
1. **One zone is biggest** (art band / card scan) and it is pictorial, not numeric.
2. **Exactly one DSEG grid** above the fold, ≤4 tiles, 24–30px — everything else DSEG
   is either the clock or below the fold.
3. **Chips are identity, not controls**: the 3–4 chips name the page subject; no
   filter consoles, no demo switches, no legend paragraphs above the first data.
4. **Calm strips between loud strips**: `eventline` / `hero-cap` (dim, 9–11px,
   chip-free) separate band → tiles → list.

### 0.2 The dense pages (wave-2 offenders, deep-diagnosed)

**`card-trends.html`** — first viewport at 390px: ticker → brandrow (wordmark +
gamechip + DSEG date plate) → 44px title → grainband → 3-button format picker → prov
line → caveat chip → **4-tile DSEG grid** → **console with 5 switches in 2 groups** →
feed header + credit chip → a **5-line legend paragraph** (`.floorkey`) → thead → rows,
where EVERY row carries art strip + bold name + context chip + pips + sparkline +
16px DSEG delta + sub-caption. Counts above the fold: **9 DSEG readouts** (date plate
+ 4 tiles + ~4 row deltas), **9 pixel chips + ~6 more chip-shaped objects** (caveat,
credit, per-row context chips), and a second 5-line legend further down for
tech-watch. No zone is larger than any other; art exists only as 30px row strips.

**`emerging-feed.html`** — first viewport: ticker → brandrow (wordmark + PRO chip +
gamechip) → title → grainband → **an API endpoint plate + PREMIUM tag** → prov →
caveat → **a demo entitlement bar (2 switches + 3-line note)** → 3-tile DSEG grid →
feed header + credit → 3-line legend → the first cluster card, which itself stacks
2–3 tags (EMERGING + tier + BREAKOUT) + pips + descriptor + provenance line + 1–2 art
exhibits + **3 DSEG reads with sub-lines** + a button + note. Counts above the fold:
**6–9 DSEG readouts, 10+ chips**, and — the worst part — two rows of developer chrome
(endpoint plate, demobar) OUTRANK the data.

The other audited pages fail the same way (full audit in §3): `s1-meta-snapshot`
shows **15–20 chips** and 5+ equal-weight zones (ramp, format picker, sort console,
movers carousel, tower) with no hero; `events-browser` fires a 4-tile DSEG grid AND a
4-group filter console (**~8–10 DSEG, 15–20 chips**) before the first event row;
`best-decks` buries its only art (the spotlight `art_crop`) BELOW the entire feed in
mobile DOM order; `home-game-switcher` renders three deliberately identical tiles with
**18+ chips** and no lead.

**The pattern:** the dense pages replaced the hero with a stat-tile grid, stacked
control/legend/dev chrome above the first data row, and demoted art to thumbnails.
Every instrument is equally loud, so none leads.

---

## 1. FOCAL HIERARCHY (enforceable rules)

### 1.1 One hero zone per page — L0

Every page declares exactly **one hero zone**:

- It is the **largest single element** on the first 390px viewport (or, for set-piece
  heroes like the s3 gallery and the deck-map canvas, it must START inside the first
  viewport and be the largest element on the page).
- It is **first in reading order after chrome**: nothing between the page header
  (title row) and the hero except at most one dim provenance/event line.
- It is one of exactly four species: **(i)** an art band (§2 tier A), **(ii)** a
  non-art hero plate (§2.4 — color-field/typographic, for OP/Riftbound/multi-game),
  **(iii)** a data set-piece (matrix, map canvas, fan chart, gallery scan, input
  dropzone), or **(iv)** an art-backed feature tile at hero scale (§2 tier D).
- Minimum size: ≥168px tall at 390px (the deck-viewer band's `min-height`), growing
  at wide breakpoints (band 210→250px per tokens §7).
- The hero carries the page's ONE display-type statement (Archivo condensed, tokens
  §2.1) — the `h1` either lives inside the hero (deck-viewer band) or directly
  introduces it (s3 title → gallery). A page never has display type in two places
  above the fold.

**A stat-tile grid is not a hero.** Grids of equal tiles are L1 by definition.

### 1.2 The loudness ladder

Four registers. Every element on a page is assigned one; an element may not borrow a
louder register's treatments.

| register | contents | treatments allowed |
|---|---|---|
| **L0 — HERO** (exactly 1) | art band / hero plate / data set-piece / feature tile | display type ≥34px, imagery, riso duotone, 4px+ shadows |
| **L1 — PRIMARY INSTRUMENTS** (≤2 zones above the fold) | ONE DSEG tile grid (≤4 tiles) and/or the main feed/table head | DSEG 20–32px, panel formula, press physics |
| **L2 — SECONDARY PANELS** | drilldowns (collapsed), method plates, rails, legends, secondary charts, tech/premium tails | DSEG ≤20px, dim labels, dashed frames, veils |
| **L3 — CHROME** | ticker, header row, format picker, provenance, caveats, credits, footer | 7–11px type, dim inks; the ticker is the only motion |

Reading order is the ladder: L3 header → L0 → L1 → data → L2. A locked/veiled module
is **always L2** — a veil may never sit above the page's hero in DOM order
(`s2-matchup-matrix` currently violates this: the PRO-locked history chart outranks
the matrix).

### 1.3 Density budget (hard caps, measured from the liked pages)

Counted in the first viewport — 390×844 mobile and 1440×900 wide. CI checks are
manual review for now; the budget is part of page acceptance.

| budget item | @390px | @1440px | source of the number |
|---|---|---|---|
| DSEG readouts (incl. clock) | **≤6** | **≤10** | deck-viewer 390 = 6; s3 390 = 5; s3 wide = 9 (clock + 4 tiles + 3 gallery stats + position) |
| DSEG tile grids | **1** (≤4 tiles) | **1** (≤4 tiles; tiles may be reparented to the rail) | s3/deck-viewer have exactly one grid |
| Press Start chips/badges/buttons (incl. WIRE badge) | **≤6** | **≤12** | liked pages: 4–5 at 390 |
| tickers / looping motion | **exactly 1** | **exactly 1** | tokens §6.4 — reaffirmed; the movers carousel and any second marquee count as violations |
| control rows (consoles/segments) above the first data row | **≤1 row, ≤2 seg-groups** | **≤1 row** (extra groups live in the rail) | liked pages have zero above the fold |
| legend / method text above the first data row | **≤1 caveat chip + ≤2 lines** | same | liked pages: one dim caption line |
| zones at equal visual weight competing above the fold | **≤2** (hero + one L1) | **≤3** | s1/events currently run 5+ |

For comparison, the measured violations: card-trends 9 DSEG / ~15 chip-objects /
2×5-line legends; events-browser 8–10 DSEG / 15–20 chips / 2 instrument rows before
data; s1 15–20 chips / 5+ equal zones / 2 scrolling strips; emerging-feed 10+ chips +
2 rows of dev chrome above data.

### 1.4 Progressive disclosure — what collapses

1. **Legends collapse.** Any legend/method text beyond 2 lines goes behind a `KEY ▸`
   press-toggle (the `op-matchup-matrix` LEADER KEY toggle is the sanctioned pattern)
   or into an L2 method plate BELOW the feed / in the wide rail. The floor keys of
   card-trends and emerging-feed must collapse.
2. **Filter consoles collapse.** One visible seg-group pair maximum (e.g. sort +
   window). Additional groups (color pips, min-field, source, type) live behind a
   single `FILT ▸` switch that expands the full console in place. The active-filter
   count chip (`6/10 SHOWN`, tokens §5.4) stays visible when collapsed.
3. **Drilldowns stay closed** (already the rule — tokens §5.8) and dock to the rail
   ≥1100px.
4. **Dev/demo chrome leaves the fold.** Demo entitlement bars, endpoint plates, and
   `PROPOSED API EXTENSION` notes move below the feed next to the method plates, or
   into the footer fine print. They are mockup scaffolding, never L1 furniture.
   (Applies today to emerging-feed and deck-classify.)
5. **Per-row instrument caps:** a feed row may carry at most **one** DSEG value, one
   chip, one spark, and one art crop. Anything more (second chip, second readout,
   sub-caption stacks) moves into the row's expand/drilldown. Emerging-feed cluster
   cards (3 tags + 3 reads + button) and meta-forecast board rows (art + code chip +
   band spark + next + delta) both exceed this and must shed into their expands.
6. **Trust chrome never collapses**: `.prov`, `.caveat`, `.credit` (ext §3–§4) are
   exempt from disclosure — but they count against the chip/legend budget, which
   forces everything ELSE to yield, not them.

### 1.5 Calm zones

- Between any two L0/L1 zones there must be a **calm strip**: ≥18px of gap containing
  at most one dim (9–11px, `--dim`) caption line — no chips, no DSEG, no borders.
  The deck-viewer `eventline` and s3 `hero-cap` are the reference implementations.
- Below the fold, no more than two consecutive loud panels; every third scroll zone
  is calm (a dim caption band, a provenance line, or plain gap).
- Feed rows are quiet by default: hairline-separated rows (`deck-viewer .crow`
  pattern — no per-row panel chrome) are preferred over panel-per-row stacks wherever
  the row is not itself a press-target for drilldown.
- The footer wordmark + fine print block (tokens §5.10) is a calm zone; nothing may
  be appended after it.

---

## 2. ART-ANCHOR SYSTEM

Card art is the one element TCG players' eyes lock onto. It is therefore rationed:
art appears at defined tiers, in defined slots, and the loudest tier appears **once
per page** (it IS the hero, or it doesn't appear at hero scale at all).

### 2.1 Treatment tiers

| tier | treatment | recipe | max per page |
|---|---|---|---|
| **A — hero art band** | duotone art crop band behind display type | tokens §4.4 verbatim: `img_art_crop` + `saturate(.72) contrast(1.08) brightness(.72)` + hard-light duotone tint + overlay grain + bottom scrim to `rgba(13,13,18,.88)` + `.band-credit` (`ART CROP: <NAME>`) | 1 |
| **B — row-level art crops** | 30–44px desaturated strips in list/tower rows, 21×29–34×24 thumbs in decklists | tokens §5.2 ID cell / §4.4 inline: `saturate(.78) contrast(1.05)`, 1px `--line` frame, `loading="lazy"` policy tokens §7.5 | one per row |
| **C — gallery / inspector full scans** | one big `img_normal` at a time | tokens §5.11 staples gallery / §5.7 inspector dock, unchanged | 1 carousel + 1 dock |
| **D — art-backed stat tile** | art crop behind a scrim, numerals on top | new component, §2.2 | 1 (and it is then the hero or the drilldown feature — never a grid of them) |

**Anti-wallpaper rule:** tiers A and D are anchors, not texture. Never tile them,
never repeat the same treatment twice on a page, never place art behind a full feed.
Tier B is the only repeating art and it is capped at one crop per row at fixed size —
ten equal thumbnails are texture, not an anchor, which is why B alone never satisfies
§1.1.

### 2.2 The scrim/contrast rule (tier D — and the legibility law for ALL art)

The law, extending tokens §4.4 and the existing "art never under data marks" rule:

- **Data numerals (DSEG) and body text never sit on raw art.** Under any numeral or
  text, the effective backdrop must be either (a) a solid plate (`--panel`/`--panel2`)
  or (b) the band scrim at its FULL stop — `rgba(13,13,18,.88)` — exactly the value
  the deck-viewer band uses under its title block. The scrim may thin to `.15–.34`
  only where nothing but the image sits on it.
- Tier-D anatomy (top→bottom): art crop (`filter:saturate(.72) contrast(1.08)
  brightness(.6)` — darker than the A-band because numbers sit closer) → duotone tint
  (optional) → grain (overlay, ≤.55, NEVER over the numeral zone) → scrim gradient
  ending ≥.88 over the lower text/numeral zone → label (10px dim uppercase) + DSEG
  value + `.sub` provenance line, all inside the scrimmed zone.
- DSEG value color keeps its semantic role (win-blue / price-orange / ink); the
  1px `--line` frame and 2px hard shadow of the panel formula (tokens §3.2) still
  apply — a tier-D tile is a `.press.cell` with a picture inside it, not a poster.
- Every tier-D tile carries the art credit (9px, `ART: <CARD NAME>`) and the standard
  `.sub` provenance/PLACEHOLDER line (tokens §5.3). If either won't fit, the tile is
  too small for art — use a plain cell.
- Premium veils (tokens §5.6) stack ABOVE the art exactly as they stack above charts;
  art never substitutes for the veil and the veil recipe is unchanged.

### 2.3 Art eligibility follows the naming tiers (ext §2)

- **T1 (curated) and T2 (card-is-name)** archetypes earn art anchors (tiers A–D),
  subject to each game's image policy (§2.4).
- **T3 (unnamed/emerging) clusters NEVER get art anchors** — no A-band, no D-tile, no
  ID-cell art tile, no CODE badge (ext §2 T3, reaffirmed). The ONE sanctioned art use
  on a T3 row is the existing **signature-card evidence exhibit** (emerging-feed's
  118×64 crops captioned `LIFT n.n`): it is evidence about cards, labeled as such,
  max 2 per cluster, inside the dashed T3 frame — it is never the row's identity
  slot and never grows past thumb scale. Marketing screenshots included.
- Formats/events are not cards: event pages and multi-game chrome use typographic /
  color-field heroes (§2.4), not borrowed card art.

### 2.4 Per-game image policy and the non-art hero

- **MTG:** Scryfall art crops / scans, hotlink OK, footer credit required
  (tokens §0). All four tiers available.
- **One Piece: NO card images** (ToS posture — owner decision of record). All four
  art tiers are OFF; use the non-art hero below. ⚠ **Compliance flag:**
  `op-deck-viewer.html` currently hotlinks Limitless CDN card images (hero leader
  card, row thumbs, dock) while `op-matchup-matrix.html` correctly renders none —
  the deck viewer must be brought onto the plate system (§3 fix list) unless the
  owner explicitly re-opens the OP image question.
- **Riftbound: NO images, ever** (no Riot CDN — owner ToS decision). Non-art hero
  only; card slots stay domain-colored placeholder frames (tokens §0).

**The non-art focal equivalent — the HERO PLATE.** Same L0 contract as an A-band
(≥168px, first after chrome, largest element), built from what we legally own:

- **Color-field:** the subject's identity hues as an oversized flat field — OP dual
  identities as the hard 45° split (the split-octagon geometry of ext §1.2 scaled to
  a band), Riftbound as fused domain plates scaled up, carrying their 2-char codes.
  Riso grain prints over the field (tokens §4.1 mask recipe); the misregistered
  second-pass offset (§4.3) gives it the print-object depth that art would have.
- **Typographic:** the subject name in Archivo condensed at 42–64px over the field,
  plus the identity chips at scale M and the axis chip (`LEADER`/`LEGEND`, ext §2 T2).
- Scrim rule applies identically: the name/readout zone sits on the ≥.88 carbon stop.
- The plate is still honest chrome: it carries the same `.prov` microline and (for
  OP) the population caveat (ext §3) in its lower band.

### 2.5 Per-page art assignment (all 14 pages)

| page | game | hero (L0) | art tiers used |
|---|---|---|---|
| `pit-wall-console/s-deck-viewer.html` | MTG | A-band (Snapcaster) — **as built, the reference** | A + B + C |
| `pit-wall-console/s3-archetype-detail.html` | MTG | staples gallery scan (as built); OPTIONAL: upgrade title block to an A-band (namesake `Murktide Regent` art crop from `s1-archetype-visuals.json`) | C + B (+A optional) |
| `pit-wall-console/s1-meta-snapshot.html` | MTG | NEW A-band: P1 archetype's rep-card crop behind the title | A + B (tower thumbs, as built) |
| `pit-wall-console/s2-matchup-matrix.html` | MTG | the matrix itself (data set-piece) | B only — rep-card crops for the two archetypes inside the drilldown |
| `card-trends.html` | MTG | NEW D-tile at hero scale: the top mover's art crop with its Δ DSEG + spark on the scrim | D + B (row strips, as built) |
| `emerging-feed.html` | MTG (T3) | typographic hero (title + top-cluster teaser card as the single focal card, dashed T3 frame) | evidence exhibits only (§2.3) — NO anchors |
| `best-decks.html` | multi | A-band: the featured winner's rep-card crop (MTG spotlight, hoisted from below the feed); OP tab swaps to hero plate | A + B (MTG rows); plates for OP |
| `events-browser.html` | multi | hero plate: featured event (typographic — event name, star plaque, DSEG field size) | none (events aren't cards) |
| `deck-map.html` | MTG | the map canvas (data set-piece), hoisted | B (inspector thumbs, as built) |
| `meta-forecast.html` | MTG | fan-chart detail panel upgraded to D-treatment: selected archetype's art crop behind the P50 readout, scrim rule §2.2 | D + B (board-row thumbs, as built) |
| `home-game-switcher.html` | multi | hero plate: the active/flagship game's livery plate (oversized wordmark + livery grainband + maturity badge), other games demoted to a secondary tile row | none (image-free page, as designed) |
| `op-matchup-matrix.html` | OP | the matrix (data set-piece), hoisted above the chrome strips | none; scaled split-octagon plate in the drilldown |
| `op-deck-viewer.html` | OP | hero plate replacing the Limitless image hero: leader name typographic hero over the split color-field (Purple Enel / Red-Black Koby) | plates only — remove CDN images (§2.4 flag) |
| `deck-classify.html` | multi | the paste/input dropzone (data set-piece) | D on the RESULT plate: classified archetype's rep-card crop behind the verdict (MTG); color-field for OP/RB |

---

## 3. ATTENTION AUDIT — all 14 pages, worst first

One line each: current hero → worst density violation → prescribed fix. Ranked so
revision agents start where the damage is.

1. **`pit-wall-console/s1-meta-snapshot.html`** — hero: none (5+ equal zones: riso-ramp, format picker, sort/filter console, movers carousel, tower); worst: 15–20 Press Start chips above the fold and a second scrolling strip (movers) competing with the ticker; **fix:** A-band hero for the P1 archetype, console collapsed to `FILT ▸` (§1.4.2), movers demoted to L2 below the tower, chip budget ≤6.
2. **`events-browser.html`** — hero: none; worst: 4-tile DSEG grid + a 4-seg-group filter console (~8–10 DSEG, 15–20 chips) fire before the first event row; **fix:** featured-event hero plate (§2.5), console → 1 row + `FILT ▸`, tiles cut to 2 and merged into the hero plate's lower band.
3. **`card-trends.html`** — hero: none (44px title then wall-to-wall equal panels); worst: 9 DSEG readouts above the fold and twin 5-line legend paragraphs; every row runs 7 instruments; **fix:** top-mover D-tile hero (§2.5), stat grid 4→2 tiles reparented to rail, both floor keys behind `KEY ▸`, rows capped per §1.4.5.
4. **`emerging-feed.html`** — hero: none; worst: dev chrome (endpoint plate + demo entitlement bar) outranks the data, and each cluster card stacks 3 tags + 3 DSEG reads + button; **fix:** typographic hero with the top cluster as the single focal card, demobar/endpoint moved below the feed (§1.4.4), cluster cards shed to 1 tag + 2 reads with the rest in the expand; T3 stays art-anchor-free (§2.3).
5. **`home-game-switcher.html`** — hero: none (three identical tiles by design); worst: 18+ chips across maturity + pip + format chips ×3 tiles, ~7 DSEG climbing; **fix:** active-game livery hero plate (§2.5), other games demoted to a compact secondary row, per-tile format chips collapsed behind the tile's ENTER press.
6. **`best-decks.html`** — hero: none; worst: the page's only real art (spotlight art crop + toplist) is DOM-last on mobile — below the whole feed; **fix:** hoist the spotlight to an A-band hero at top (§2.5), tab-bar maturity badges shortened to chips (full sentence moves to `.prov`), feed rows stay quiet hairline rows.
7. **`meta-forecast.html`** — hero: partial (fan-chart detail panel, diluted); worst: mode banner + two-part control bar wedge between header and data, and board rows carry 4+ instruments each; **fix:** detail panel becomes the D-treatment hero (§2.5), mode/demo controls move below the board, rows capped per §1.4.5.
8. **`op-deck-viewer.html`** — hero: YES (leader band — the only wave-2 page with one); worst: a 4–6-tile equal-loud DSEG grid immediately undercuts the hero, and the page hotlinks OP card images against the ToS posture; **fix:** replace image hero with the split color-field hero plate, thumbs → `thumbph` placeholders (§2.4 flag to owner), tile grid → ≤4 with price/leader demoted to the list header.
9. **`op-matchup-matrix.html`** — hero: none (matrix deferred); worst: four consecutive full-width chrome strips (caveat → matrix-note → pip legend → key toggle) before the page's only instrument; **fix:** hoist the matrix to L0 directly under the title, merge caveat+note into one 2-line strip, pipkey joins the existing `KEY ▸` toggle.
10. **`deck-classify.html`** — hero: the display title only; worst: demobar with two Press Start seg-groups (3 games + 2 tiers) + endpoint plate + caveat stacked under the title before the input; **fix:** the input dropzone becomes the hero directly under the title; demo/endpoint chrome moves below the result; result plate gets the D-treatment rep card (§2.5).
11. **`pit-wall-console/s2-matchup-matrix.html`** — hero: none (and a LOCKED chart outranks the matrix); worst: the PRO-veiled history chart sits above the matrix in DOM order — a veil above the hero violates §1.2; **fix:** matrix hoisted to L0, history demoted below it as V-PANEL (ext §5), drilldown gains tier-B rep-card crops (this MTG page currently has zero art).
12. **`deck-map.html`** — hero: YES (the canvas) but pushed below a 4-tile DSEG grid + fly-to chip strip; worst: the hero starts at/after the fold edge; **fix:** map hoisted directly under the title; hulls/points/decks/noise tiles become map-corner DSEG chrome (like the existing zoom/compile stamps) or rail plates; fly-to strip overlays the map top edge.
13. **`pit-wall-console/s3-archetype-detail.html`** — hero: YES (staples gallery at fold 2; tiles ≤4, chips 4) — compliant; worst (minor): title block is the only v3 identity zone without imagery; **fix (optional):** A-band behind the title using the namesake art crop; no other change.
14. **`pit-wall-console/s-deck-viewer.html`** — hero: YES (the duotone band) — the reference implementation; worst: none at 390px (6 DSEG incl. clock is the budget ceiling); **fix:** none — freeze as the calibration page for §1.3.

---

## 4. Kept faith — existing rules this spec does not touch

- **Chart data-ink stays crisp vector** (tokens §0); heroes and art never replace or
  texture data marks; grain never sits over unlocked data (tokens §4).
- **DSEG: no ghost underlay, ever** (tokens §2.2). Reducing DSEG COUNT per §1.3 never
  changes DSEG treatment; unlit `--.-` states (ext §3) are unaffected.
- **Art never under body text or data numerals without §2.2's scrim stop** — this
  spec makes the previously implicit rule explicit and mandatory.
- **T3 emerging clusters never get art tiles / identity anchors** (ext §2, §2.3 here).
- **Premium veil system unchanged** (tokens §5.6, ext §5): same three scopes, same
  choreography; the only new constraint is placement (a veil is L2 — never above the
  hero).
- **Trust chrome (`.prov`, `.caveat`, `.credit`) never disclosed away** (ext §3–§4);
  the density budget is met by demoting controls, legends, and dev chrome instead.
- Blue/orange diverging scale, purple scarcity, press physics, motion grammar,
  390px-first + ≥1100px spread: all unchanged (tokens §1, §3, §6, §7).

## 5. Open items for the owner (stop-and-ask, not guessed)

1. **One Piece imagery conflict (§2.4):** `op-deck-viewer.html` hotlinks Limitless
   CDN card images; `op-matchup-matrix.html` and the token spec's posture say no OP
   images without grounded local URLs. This spec prescribes removal (hero plate
   instead) — confirm, or explicitly bless Limitless hotlinking and this spec's OP
   rows revert to tier B thumbs.
2. **s3 optional A-band (§2.5):** the owner likes s3 as-is; the namesake art band is
   proposed, not required — bless or drop.
3. **Density budgets as CI gates:** §1.3 is manual-review acceptance for now; if the
   owner wants it automated, a fixture test counting DSEG/chip nodes in the first
   viewport per page is the follow-up.
