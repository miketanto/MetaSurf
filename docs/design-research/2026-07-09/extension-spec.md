# PIT-WALL CONSOLE — DESIGN-LANGUAGE EXTENSION SPEC (multi-game + wave-2 pages)

**Status:** v1 draft for owner review, 2026-07-09.
**Base system:** `docs/design-research/2026-07-09/pit-wall-tokens.md` (cited below as
**tokens §n**). Nothing in this spec overrides the token spec; it extends it.
**Grounding:**
- `docs/design-research/2026-07-09/riftbound-games-ground.json` (cited as **ground**) —
  contains the full `game_ui_registry` for all three games (mtg / onepiece / riftbound),
  the Riftbound catalogue facts, API shapes, and attribution config. *Note: no separate
  `onepiece-ground.json` exists in this worktree; the One Piece registry values below come
  from `ground → game_ui_registry.games.onepiece`.*
- `/Users/michaelsutanto/MetaSurf/docs/notes/onepiece-limitless-observed-schema.md` and
  `.../overnight-blockers-onepiece.md` (cited as **OP-schema** / **OP-blockers**) — real
  observed One Piece source structure, deck labels, and data limits.
- `docs/design-research/2026-07-09/s1-archetype-visuals.json` — MTG archetype grounding.
- Contrast figures marked *(computed 2026-07-09)* are WCAG relative-luminance ratios
  computed this session against `--panel #14141a` / `--bg #0d0d12`; nothing else in this
  document is a measured number unless labeled as such.

Every decision below is stated as **DECISION**, with a one-line alternative only where the
call was genuinely close.

---

## 0. The invariant shell and the livery layer

**DECISION — hub-and-spoke with a bounded livery layer.** The carbon shell (palette,
DSEG numerals, press states, blue-orange winrate scale, layout grammar — tokens §1–§7)
is invariant across all 6–8 games. Per-game identity ("livery") is exactly three things —
one accent hue, one riso-grain gradient recolor, the game's wordmark — applied to exactly
three slots: the **game-switcher tile**, the **page-title underline rule** (the 4px
grainband of tokens §4.3, recolored), and the **active game indicator in the header**.
Livery never touches layout, typography, numerals, the winrate scale, or chart data-ink.
This sits deliberately between op.gg's undifferentiated uniformity and Untapped's
subdomain split (research: untapped.gg hub-and-spoke, https://untapped.gg/en; op.gg
maturity badges, https://op.gg/; melee.gg game-as-enum floor,
https://melee.gg/Home/About). Game identity in code stays `game_id`-keyed data — route
slugs `/{game}/{format}/...` per **ground** `game_ui_registry.lookup` — mirroring the
repo's game-neutrality rule.

**Theming gradient by surface** (research: untapped.gg companion,
https://untapped.gg/en/installed): full livery on switcher + game home; header-rule +
pips only on meta tables and archetype pages; **zero livery** on trust chrome — as-of
stamps, n counters, window selectors, DSEG blocks — so a One Piece winrate and an MTG
winrate are visually the same species of number.

**Livery accents (provisional, owner to bless — same status as the riftbound.ts hues,
ground `gaps_and_honest_limits[1]`):**

| game | accent | rationale |
|---|---|---|
| mtg | none — product-default cool-white chrome | flagship; the default console IS its livery |
| onepiece | `#e0b73a` (the registry Yellow) | 9.61:1 on `--panel` *(computed 2026-07-09)*; not blue/orange/purple, so no winrate-scale or sector-purple collision |
| riftbound | `#3aa7a3` (the registry Calm teal) | 6.32:1 on `--panel` *(computed)*; distinct from `--win #3b9dff` in hue and role |

Livery tokens live in a versioned `metasurf-liveries.json`, config over code, every hue
contrast- and CVD-checked before merge (research: TeamColors token dataset,
https://teamcolors.jim-nielsen.com/). Alternative if teal/blue proximity worries the
owner: Riftbound takes Order gold `#c9a13b` and One Piece keeps yellow — they are close
neighbors, so only do this if teal fails a CVD check.

**Game-tile maturity badge** (research: op.gg "Stats/Beta/Soon" labels): every switcher
tile carries a data-maturity chip — `FULL TELEMETRY` (MTG), `LIMITED SAMPLE — 849 ONLINE
MATCHES` (One Piece), `CATALOGUE ONLY — NO MATCH DATA` (Riftbound). Chip text is Press
Start 2P 7px (NOT DSEG — DSEG7 has no letterforms, tokens §2.1; the research suggestion
to set the chip in DSEG is unimplementable as written); the numeral `849` inside it may
render DSEG 12px. The as-of date prints on the tile in the standard provenance microline
(§4 below). The caveat is part of the game's identity, not a footnote.

---

## 1. Pip / swatch system per game

### 1.1 One grammar, three silhouettes

**DECISION.** One proprietary chip grammar for all games — a flat hue field, 1px rim,
optional letter(s), hard shadow — in the 2px-press mechanical language. Per-game
**silhouette cue** so any screenshot of a table is attributable to its game (research:
Lorcana shape+hue dual coding, https://wiki.mushureport.com/wiki/Ink; F1 team-color bar +
3-letter code, http://mattbirkett.co.uk/wp/project/f1-tv-graphics/):

| game | silhouette | why |
|---|---|---|
| MTG | **circle** | already sanctioned (tokens §1.4 `.pip{border-radius:50%}` — the one border-radius exception); colorless stays the gray diamond |
| One Piece | **octagon** (cut-corner square, `clip-path:polygon(25% 0,75% 0,100% 25%,100% 75%,75% 100%,25% 100%,0 75%,0 25%)`) | angular cut per the research recommendation; cannot be confused with the MTG circle or the colorless diamond |
| Riftbound | **rectangular plate(s)** carrying a 2-char code | domains are words; a hue-only micro-shape across 6 domains where *every* legend is 2-domain is unreadable — the label is mandatory |

**Legal constraint (hard):** no official mana/tap glyphs anywhere, ever — WOTC's Fan
Content Policy lists them as restricted trademarks and a premium-gated product cannot
shelter under the policy; the Mana font's SVG glyphs remain WotC copyright (research:
https://company.wizards.com/en/legal/fancontentpolicy, https://mana.andrewgioia.com/).
Hues + letterforms are ours; glyph shapes are not. The same posture applies by default to
One Piece color symbols and Riot's Riftbound domain icons (owner ToS decision: no Riot
assets — **ground** `IMAGE_POLICY_CRITICAL`).

### 1.2 Two scales

- **Scale S (density: tower rows, matrix heads, feed rows):**
  - MTG: existing 9px letterless dots, WUBRG order, one dot per color (tokens §1.4,
    unchanged). MTG identities are sets of up to 5 — the cluster is the atom.
  - One Piece: 10px octagon(s). Identities are 1–2 colors (**ground** onepiece notes:
    "multicolour cards carry two codes"); dual identities render **one split octagon** —
    hard 50/50 diagonal split at 45°, first color (by registry `pipOrder`
    Red→Green→Blue→Purple→Black→Yellow) upper-left. Never a gradient (gradients are
    reserved for riso accents), never two separate dots — the pair is the atom, exactly
    the Lorcana meta convention where "Amber/Emerald" is the tracked unit (research:
    https://inkdecks.com/lorcana-metagame/inks). Matches observed source labels
    "Red/Black Koby", "Purple Enel" (**OP-schema §1**, **OP-blockers #4**).
  - Riftbound: no letterless variant exists. Minimum rendering is the twin plate
    (scale M) — see below.
- **Scale M (identity slots: archetype header, drilldown, tooltip, legend strips):**
  - MTG: 16px circle with 1-char letter (the "letter-dot").
  - One Piece: 16px octagon with 1-char letter; dual = two **fused** letter octagons
    (second chip `border-left-width:0`, tokens §5.4 fused-segment grammar), zero gap —
    still one visual atom.
  - Riftbound: fused twin plates, each 20×16px, each half carrying its 2-char code over
    its domain hue: `[FU|CH]`, `[CA|MI]`. Single-domain cards (runes, mono spells —
    **ground** `domain_facts`) render one plate. Battlefields render the Colorless plate
    (`--`, gray `#8a919e`).

In-chip letters: Press Start 2P 6px, per the sanctioned deck-viewer cost-pip precedent
(tokens §1.4). The §2.1 7px floor governs chrome *text*; chip letters are dual-coded
graphics (hue + shape + aria-label + legend strip), not prose.

### 1.3 Letter / code assignments

- **MTG:** the codes themselves — `W U B R G C` (**ground**
  `game_ui_registry.games.mtg.pipOrder`).
- **One Piece:** `R G B P K Y`. Black takes **K** to break the Black/Blue initial
  collision — the CMYK key-plate convention, natively on-brand for a risograph design
  language. *Alternative (close call): 2-char codes `RD GN BU PU BK YW` if the owner
  finds K too print-nerd; costs 6px of width per chip.*
- **Riftbound:** `BO CA CH FU MI OR` — the first two letters are unique across all six
  domains (Body/Calm/Chaos/Fury/Mind/Order, **ground** `riftbound_catalogue.domains`).
  Colorless = `--`.

These are exactly the "per-code short-label extension to GameUiConfig" flagged as a
registry seam gap (**ground** `registry_seam_gaps[0]`, **OP-blockers #3**): this spec
resolves that gap — add optional `shortLabel: Record<code,string>` to `GameUiConfig`
with the values above; `ColorPips` renders `shortLabel[code] ?? code`.

### 1.4 Hues, rims, dark-surface tuning

Chip fills are the registry `pipPalette.bg` values verbatim (**ground**
`game_ui_registry.games.*`). Tuning for the carbon surfaces *(all ratios computed
2026-07-09)*:

- **Rim:** default `1px solid rgba(242,242,247,.25)`. The two near-black hues — MTG `B`
  and OP `Black`, both `#2b2b33` — sit at **1.31:1** against `--panel` and vanish without
  help: they take the bright rim `#a6a1a0` (tokens §1.4 already does this for `pip-B`).
  OP `Purple #7b4fa6` is borderline at **3.07:1** — passes the 3:1 graphical floor,
  standard rim, watch it in review.
- **Letter ink:** `var(--bg) #0d0d12` on every chip **except** MTG-B / OP-Black (light
  fg `#c9c4d2`, 8.23:1) and OP-Purple (light fg `#f3eafd`, 5.13:1). Dark ink beats the
  registry light `fg` everywhere else — e.g. Green/Body 5.66 vs 3.10, Blue/Mind 4.55 vs
  3.78, Calm 6.68 vs 2.63. Weakest results are Chaos 4.17 and Fury/Red 4.40 — below
  4.5:1 text-AA but above the 3:1 graphics floor; acceptable because the letter is
  redundant coding (hue + silhouette + aria-label + legend), and the chips are
  fixed-size UI glyphs, not body text.
- **Identity-vs-performance firewall:** OP Blue / MTG U / Mind (`#3b7bd0`) neighbors
  `--win #3b9dff`, and Red/Fury (`#d3492f`) neighbors `--loss #ff7a1a`. Rule: identity
  hues appear **only** inside rimmed, shaped chips; performance hues appear **only** on
  numerals, deltas (always with `▲▼` glyphs, tokens §8), heat fills, and strokes — never
  as a filled chip containing a letter. A red chip can never be misread as "losing"
  because losing is never a chip. (Research warning: TeamColors / CVD collision note.)

### 1.5 Legend and tooltip pattern

- **Legend strip** (`.pipkey`) at first use per page, in the plaque-legend position
  (tokens §5.5): 9px dim uppercase, letter-spacing `.08em`, each entry a scale-M chip +
  full word: `BO BODY · CA CALM · CH CHAOS · FU FURY · MI MIND · OR ORDER`. One Piece:
  `R RED · G GREEN · B BLUE · P PURPLE · K BLACK · Y YELLOW`. MTG pages may omit it
  (grinders know WUBRG); OP and Riftbound pages must not.
- **Tooltip:** fine-pointer hover on any chip reuses the floating-preview tier (tokens
  §5.7 tier 2) as a micro variant — full word(s) + the chip at 24px. Touch gets **no**
  per-chip tap target (chips are sub-44px; the row is the target, tokens §3.4) — the
  legend strip and `aria-label` carry it. Every chip cluster:
  `role="img" aria-label="colors: red, black"` / `"domains: fury, chaos"`.

---

## 2. Archetype naming tiers

Three visual registers, mapped to how the name was produced. The register encodes
provenance as visual weight (research: iA Writer greyed AI text / Carbon AI label,
https://www.shapeof.ai/patterns/disclosure,
https://carbondesignsystem.com/components/ai-label/usage/).

### T1 — CURATED (rule-file names)

E.g. "Izzet Murktide", "Rakdos Scam" (`s1-archetype-visuals.json`; definitions ported
from MTGOFormatData, never authored — CLAUDE.md rule 4). Render: JetBrains Mono 700
13px `var(--ink)` — the tokens §5.2 tower-row name, unchanged. Full art tile, full CODE
badge. This is the reference register; nothing else may imitate it.

### T2 — STRUCTURAL (card-is-name)

The archetype IS a card: One Piece leaders (`archetype_axis: leader` — **OP-schema §3**),
Riftbound legends (`archetype_axis: legend` — **ground** `deck_shape`). Names like
"Purple Enel", "Red/Black Koby", "Ahri - Nine-Tailed Fox" are real permanent product
names, so they get **full weight** (JetBrains 700, ink) — NOT the provisional dimming.
Distinguishers:

- **Axis chip** after the name: `LEADER` / `LEGEND`, Press Start 2P 7px, `--dim` on
  `--panel2`, 1px `--line` border — states "this name is a card, not editorial".
- **Dim set-id**: the disambiguating base id renders as a 10px `--dim` suffix chip —
  `(ST01-001)`. **DECISION:** always shown on detail pages (provenance-forward); in
  dense rows only when the label collides — exactly matching the structural-rule data,
  which appends the id only for the 11 colliding labels like "Red Monkey.D.Luffy
  (ST01-001)" vs ST21-001 (**OP-blockers #4**). The id is card data, never invented.
- Color identity via the game's chip system (§1), which doubles as the split-color part
  of the community label ("Red/Black" → split octagon + "Koby").

### T3 — UNNAMED / EMERGING (machine-detected clusters)

Fed by `GET /v1/{game}/{format}/emerging`: `named` is **always false** in this feed,
`provisional_descriptor` is "colour group + top signature card, flagged 'Unnamed:'",
`cluster_key` is not a stable id (**ground** `api_shapes`). Render:

- **Dashed frame:** `border:1px dashed #3a3a48` (chart-framing gray, tokens §1.3) on the
  row/card — visibly not a finished plate; no hard 2px shadow (unearned solidity).
- **EMERGING tag:** Press Start 2P 7px, `--dim` on `--panel2`, `1px dashed #3a3a48`
  border. Not orange (orange is a performance/caveat ink), not purple (best-in-class
  only, tokens §1.2).
- **Provisional descriptor** in JetBrains Mono **400** (never 700) at a dedicated
  reduced-contrast token `--provisional:#b9b9c3` (between ink and dim). Never Archivo
  display face, never an art tile, never a CODE badge — those are earned by T1/T2.
- **Persistent provenance chip**, action-specific, never dropped as the cluster grows:
  `AUTO-CLUSTERED · 37 LISTS · FIRST SEEN 2026-06-28` (fields: `n_decks`,
  `first_seen`). Framed as scanner telemetry, not disclaimer — in a
  numbers-you-can-trust brand, machine detection with printed n reads as rigor
  (research: Carbon AI label + trust caveat, PMC12166545).
- Signature-card line: `TOP SIGNAL: <SignatureCard.name> · LIFT n.n` (lift from the
  schema; any mockup value labeled PLACEHOLDER).
- **Graduation:** when a rule file lands, the row re-renders as T1 and fires one one-shot
  RGB glitch (tokens §6.3) — a legitimate changed-data trigger, and the legible
  "name snaps to full weight" moment from the iA Writer pattern.

**Never** style T3 like T1 — no exceptions, including marketing screenshots.

---

## 3. Degradation states — one caveat-chrome component, several messages

**DECISION — a single `.caveat` component**; every data-quality condition is a message
in it, never a bespoke widget (research: NN/G + Carbon per-widget honest empty states,
https://www.nngroup.com/articles/empty-states-pattern/):

```css
.caveat{
  display:inline-flex; align-items:center; gap:6px;
  font:400 9px 'JetBrains Mono',monospace; letter-spacing:.08em; text-transform:uppercase;
  color:var(--dim); background:var(--panel2);
  border:1px solid var(--line); border-left:3px solid var(--loss);  /* orange keel */
  padding:4px 7px;
}
.caveat b{ color:var(--ink); font-weight:700; }   /* the load-bearing number/term */
```

The orange keel is a non-performance use of `--loss` alongside sideboard chrome and
price tiles (sanctioned by tokens §1.2). Never red, never an icon.

**Message catalog** (canonical strings; numbers always live data, `<b>`-wrapped):

| state | message | trigger / grounding |
|---|---|---|
| Share-only mode | `SHARE-ONLY FEED — NO PAIRINGS PUBLISHED · WINRATES UNAVAILABLE` | OP offline site events carry `Rounds:null`, standings are Rank+Player only (**OP-schema §1, §3**). All WR readouts in scope render unlit DSEG `--.-` (tokens §8 / research: Google Trends refusing unstable values, https://support.google.com/trends/answer/4365533) |
| Small n | `LOW SAMPLE · N=12 / FLOOR 40` | below the stated per-metric floor; pairs with the §5.9 hatch overlay and the unlit `--.-` readout; the floor is printed, never implied |
| Population caveat | `ONLINE POPULATION ONLY · N=849 MATCHES` | One Piece match data is online-platform only (play.limitlesstcg API — **OP-schema §2**; 849 per owner brief). Persistent on **every** OP stat module, page-level once + short echo on modules |
| Top-cut share | `TOP-CUT SHARE — TOP 64 PUBLISHED OF 1,541 ENTRIES` | offline regionals publish Top 64 only; denominators are top-cut share, not field share (**OP-blockers #2**, fixture t431). Footnote variant directly under any OP share table fed by offline majors |
| No feed | `NO MATCH DATA FEED — CATALOGUE ONLY` | Riftbound: zero decklists/events/winrates exist (**ground** `gaps_and_honest_limits[0]`). Full module chrome renders with unlit readouts — wired-up and waiting, never faked |

**Placement rules:** page-population caveats sit once under the format picker and echo in
the provenance footnote (§4); module caveats sit in the panel-header right slot;
cell-level low-n uses the hatch + legend entry (tokens §5.9) — in the visualization
itself, not only in prose. Max two caveat chips visible per module; when the page-level
population chip is present, module chips use the short form (`ONLINE ONLY · N=849`).
Layout is preserved in every degraded state — the module still shows what it is for.

---

## 4. Attribution slot + provenance chrome standards

### 4.1 Attribution (required credits)

API contract: `EventsResponse.credits` carries `Credit{source,name,url,attribution,
required}`; `topdeck.gg` and `melee.gg` are `required:true`, `mtgo.com` is not
(**ground** `api_shapes.attribution`). **DECISION — required credits render twice:**

1. **Visible chip in the data-zone header** (`.credit`): `DATA: TOPDECK.GG ↗` —
   JetBrains 700 9px, `--ink` name on `--panel2`, 1px `--line`,
   `<a target="_blank" rel="noopener">` to `Credit.url`, the `↗` deep-link glyph from
   tokens §5.11. Shown whenever the module's rows include that source; always above the
   fold with the module, never scroll-hidden, never veiled (§5).
2. **Verbatim attribution string in the provenance footnote** (tokens §5.10 position):
   `DATA PROVIDED BY TOPDECK.GG` — the `Credit.attribution` text exactly, linked.

Non-required credits (mtgo.com) appear in the footnote only. Trust is furniture, not
footer — the same move as Kalshi surfacing its regulator in-product (research:
https://avark.agency/learn/prediction-market-design-patterns).

### 4.2 Provenance microline — the `.prov` standard

One canonical order, everywhere: **WINDOW · N · AS-OF** —

```
LAST 14D · N=412 DECKS · AS-OF 2026-07-08
```

9–10px dim uppercase (tokens §5.10 typography). Every data panel header carries a
`.prov` or visibly inherits the page-level one; tooltips and drilldowns repeat n and
window inside themselves (tokens §5.2 CI rule; research: Polymarket printing volume
under every market). Forecast modules extend `.prov` with a resolution clause
(research: Metaculus resolution criteria as first-class UI,
https://www.metaculus.com/faq/):
`RESOLVES VS CHALLENGE RESULTS · WINDOW 2026-07-01 → 07-14`.

Compiled artifacts (cluster map) stamp `LAYOUT COMPILED 2026-07-08` in DSEG in the
corner (research: Map of GitHub precomputed tiles,
https://github.com/anvaka/map-of-github).

---

## 5. Premium locked-state standard — the misprint veil at three scopes

The §5.6 misprint veil (tokens) is the only gate chrome. Three sanctioned scopes; all
share the invariants: veil sits over **genuinely computed pixels** (run the real query,
render the real chart, veil it — never placeholder content behind the blur); trust
metadata (`.prov`, `.caveat`, `.credit`) prints **outside/on top of** the veil, crisp;
free tier receives masked payloads server-side (`+?.?▲`, pre-quantized series), never
true values in the DOM (tokens §5.6, §8; research: access-paywall "see just enough",
https://ui-patterns.com/patterns/Paywall).

| scope | treatment | use |
|---|---|---|
| **V-PANEL** | tokens §5.6 verbatim: riso veil + stepped defocus + `PRO · LOCKED` chip; unlock = 12-step squeegee wipe | a whole module (matchup history pane, distribution toggle) |
| **V-COLUMN** | veil absolutely positioned over the column's cells only (`table-layout:fixed` keeps geometry stable, tokens §5.9); column header stays crisp and carries the chrome-bordered `PRO` chip (tokens §5.11); masked values `+?.?` | one premium column in a free table (e.g. matchup-conditioned WR) |
| **V-FEED** | first 3 rows crisp and fully interactive; **one** continuous veil block over the remainder with a single chip stating the size of the locked tail: `PRO · 14 MORE ROWS — LOCKED`; `.prov` for the whole feed prints above the veil | a ranked feed where depth is the product (emerging scanner tail, movers beyond top 5) |

Rules: **max one veil per scroll zone** — never checkerboard per-row veils, never
stacked veils; chrome (header, provenance, attribution, caveats) is never veiled; the
unlock choreography is always tokens §6.5 (quantized steps, reduced-motion = instant);
depth axes that gate by resolution (fan-band count, series resolution) use the s3
resolution-gate variant. Premium is depth within the screen — a veil never replaces a
page, and the free face of every gated module is still honest (point estimate + one
band; central line free, full fan premium — research: Bank of England fan chart bands,
https://www.visualizing.org/fan-chart; Metaculus depth-on-demand toggle).

---

## 6. Per-page component plans — the 10 wave-2 mockups

Numbering continues the existing s1–s3 + deck-viewer set. Every page: 390px-first +
≥1100px spread (tokens §7), wire ticker, provenance footnote, reduced-motion contract.
"New" = genuinely new components introduced by this spec; everything else is reuse.

### S4 — Game Console Home (switcher)
- **Reuses:** panel formula + press tiles (§3.2–3.3), grainband (§4.3, livery-recolored
  per game), DSEG stat tiles for per-game headline counts, `.prov` per tile.
- **New:** game tile (livery slot #1: accent + riso gradient + wordmark), **maturity
  badge** (§0), equal-sized tile grid — the untapped.gg chooser in console idiom; the
  MetaSurf wordmark stays top-left in every game section, the product brand never yields
  to the game brand.
- **Degradation:** the badge IS the degradation state; Riftbound tile readouts unlit.

### S5 — One Piece Meta Snapshot (s1 clone)
- **Reuses:** timing tower (§5.2) with the ID cell's art tile replaced by a color-framed
  leader placeholder (no image URLs in grounding — **ground** `IMAGE_POLICY_CRITICAL`),
  console switches (§5.4) with `.fpip` filters rebuilt on the six OP octagons, DSEG
  tiles, drilldown dock.
- **New from this spec:** OP octagon pips incl. split duals (§1.2), T2 structural name
  rows with axis chip + collision set-ids (§2), page-level `ONLINE POPULATION ONLY ·
  N=849 MATCHES` caveat + `TOP-CUT SHARE` footnote on offline-major share tables (§3),
  `.pipkey` legend strip.
- **Gating:** V-COLUMN on matchup-conditioned WR.

### S6 — One Piece Leader Detail (s3 clone)
- **Reuses:** s3 named-area bench grid, star plaque/league badge, deck feed rows, staples
  gallery — gallery card scans become color-framed placeholders with card name +
  `data-id` (cards cite as `OP15-058`, never bare names — **OP-schema §1**).
- **New:** T2 header register (full-weight name + `LEADER` chip + dim set-id + fused
  letter octagons); share-only caveat on the WR pane for offline-sourced rows (unlit
  `--.-`); online-match WR pane carries the population chip.
- **Gating:** V-PANEL on the matchup-spread pane.

### S7 — One Piece Event Page (grounded on Regional Bielefeld t431)
- **Reuses:** deck feed rows (§5.11) for the Top-64 standings, star plaque (1,541
  players = ★★★★★), format picker, copy/export bar on expanded decklists (Leader 1 +
  main 50 — **OP-schema §1**).
- **New:** event header plate with `.caveat` `TOP-CUT SHARE — TOP 64 PUBLISHED OF 1,541
  ENTRIES`; `.credit` slot wired to `EventsResponse.credits` (TopDeck/Melee events show
  the visible chip, §4.1); missing-rank rows (drops with null placing — **OP-schema §2**)
  print record without rank, never a fabricated position.
- **Gating:** none — event pages are trust surfaces, keep them free.

### S8 — Riftbound Legend Index (36 legends)
- **Reuses:** tower rows (§5.2) minus spark/WR/Δ columns; format picker; DSEG only for
  catalogue counts.
- **New:** fused twin-plate domain swatches as the ID cell (§1.2) — e.g. `[CA|MI]` Ahri,
  `[FU|CH]` Jinx (**ground** `legends_all_36_base_nonpromo`); T2 register with `LEGEND`
  axis chip; every stat column unlit `--.-` under the page-level `NO MATCH DATA FEED —
  CATALOGUE ONLY` caveat; `.pipkey` strip mandatory. Sort by domain pair, set (OGN/SFD/
  UNL), name.
- **Gating:** none — never veil a page that has no data (a veil implies computed pixels).

### S9 — Riftbound Catalogue Browser
- **Reuses:** deck-viewer list rows (§5.7) — count column dropped; type-group order
  Legend→Unit→Spell→Gear→Battlefield→Rune (**ground** `typeGroupOrder`); card inspector
  dock with **domain-colored placeholder frame + card name** instead of an image (owner
  ToS decision — no Riot CDN); DSEG for energy/might/power attributes (ints or null —
  **ground** `attribute_semantics`), null renders unlit.
- **New:** deck-shape plate (legend 1 · main 40+ · runes 12 · battlefields 3, from
  `deck_shape` — note main is min-40, not exactly 40); no-legality notice (Riftcodex has
  no legality field — recorded owner blocker).
- **Gating:** none.

### S10 — Emerging Scanner (MTG; the discovery feed)
- **Reuses:** tower grid, `.prov`, one-shot glitch on promotions, press switches.
- **New:** T3 rows in full (§2 — dashed frame, EMERGING tag, `--provisional` mono
  descriptor, AUTO-CLUSTERED chip, signature-card lift line); **tier ladder chips**
  `SCOUTED → PROVISIONAL → CONFIRMED` with the promotion rule printed on the chip
  itself: `PROVISIONAL — N=23 / 2 EVENTS · CONFIRMS AT N≥50` — tier computed from
  `n_decks`/`recent_decks`/window, never editorial (research: ThoughtWorks Radar rings,
  https://www.thoughtworks.com/radar); separate **RISING** (recent_decks) and **SHARE**
  columns, never blended; near-zero-baseline growth suppresses the meaningless % for a
  riso-orange `BREAKOUT · 14 LISTS · LAST 7D` flag; below-floor readouts `--.-` +
  `NOISE FLOOR` caption (research: Google Trends Rising/Top + Breakout).
- **Gating:** the emerging endpoint is premium (**ground** `api_shapes`): free face
  shows the top-3 clusters, V-FEED veils the tail.

### S11 — Movers Board (copies-per-week ledger)
- **Reuses:** tower-row grid, delta chips `+x.x▲/−x.x▼`, spark SVG framing, press
  segment for the 1W/4W window toggle, `.prov` header
  (`WINDOW 2026-06-08 → 2026-07-08 · 41 EVENTS · N=1,204 DECKS` pattern).
- **New:** stacked **RISERS / FALLERS** boards (the genre-standard winners/losers
  ledger — research: MTGGoldfish Movers,
  https://www.mtggoldfish.com/movers/paper/modern); **min-sample slider** as first-class
  filter — below-floor rows don't vanish, they render under a mini-veil with
  `N=12 — BELOW FLOOR` printed on it (research: untapped.gg 500+ games threshold,
  https://mtga.untapped.gg/constructed/standard/cards).
- **Gating:** free = Δcopies + share; V-COLUMN on window-comparison depth.

### S12 — Archetype Cluster Map
- **Reuses:** timing-tower rail (persistent, right, sticky — §7.3), pit-board tooltip
  with DSEG WR + `n=37 · window` line, one-shot glitch on weekly layout refresh,
  `.prov` + `LAYOUT COMPILED <date>` DSEG stamp.
- **New:** single-Canvas point field (1–10k points → Canvas, SVG/DOM overlay for
  labels/highlight/captions — research: renderer benchmarks,
  https://blog.scottlogic.com/2020/05/01/rendering-one-million-points-with-d3.html);
  riso-grain density fills at low zoom (grain = density encoding); Voronoi hit-find with
  max-radius clamp; semantic-zoom labels from rule files only (cool-white UI face, never
  DSEG — names aren't numbers); fixed anti-over-reading caption `POSITION = DECK
  SIMILARITY, NOT STRENGTH · LAST 8 WEEKS · N=1,204 DECKS · AS-OF <date>` (research:
  Nomic Atlas, https://docs.nomic.ai/atlas/datasets/data-maps); mobile mode:
  search-to-fly pinned top, nearest-point snap → bottom sheet, 44pt cluster-label
  targets, dots display-only (research: Map of GitHub mobile,
  https://anvaka.org/map-of-github/). T3 clusters on the map render with dashed halo +
  EMERGING label, never a T1-style name.
- **Gating:** map free; brush-to-crossfilter into the event table/movers = V-PANEL on
  the linked panels.

### S13 — Meta-Share Forecast Module
- **Reuses:** DSEG readouts + quantized roll-up (the 200–300ms animated-counter
  guidance is natively the §6.1 roll-up), `.prov` with resolution clause (§4.2),
  press toggle for point/distribution view.
- **New:** stepped fan chart — 2–3 **hard-edged** probability bands, discrete, labeled
  at the right edge in DSEG (`50% BAND 4.8–7.2%`), no alpha fades (they die on carbon;
  research: BoE fan chart accessibility); bands render in **neutral carbon-grey steps**
  and only the central line uses the winrate scale, so uncertainty is visually a
  different substance than performance and a wide band cannot read as "strong"
  (research: hurricane cone-of-uncertainty misreadings, WCAS-D-21-0173); plain-language
  caption `WHERE THE NUMBER COULD LAND — OUTCOMES CAN FALL OUTSIDE THIS BAND`; lead
  readout `FAVORED · 64%`-style plain percentage, methodology secondary (research:
  prediction-market display conventions); low-n decks swap the band for an **event-tick
  strip** — one tick per actual event, n countable by eye.
- **Gating:** free = central line + one band; V-PANEL resolution gate unlocks the full
  fan + CDF toggle on the same panel (Metaculus depth-on-demand).

---

## 7. Open items for the owner (stop-and-ask, not guessed)

1. **Livery accents** (§0) — provisional hues need sign-off, same status as the
   riftbound.ts palette.
2. **`shortLabel` registry extension** (§1.3) — this spec proposes the concrete values;
   it is the flagged `registry_seam_gaps[0]` / OP-blockers #3 seam change (shared file).
3. **OP Black = K vs 2-char codes** (§1.3 alternative).
4. **Top-cut share semantics** (§3) — the chrome is specified either way, but
   OP-blockers #2's product question (is Top-64 share an acceptable semantic?) is still
   an owner call; if excluded, S5/S7 swap the footnote for a `SHARE ROLLUP EXCLUDED —
   TOP-CUT ONLY SOURCE` caveat.
5. **Same-name leader merging** (OP-blockers #4) — affects whether T2 set-id chips are
   disambiguators or decoration.
