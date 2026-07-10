# PIT-WALL CONSOLE — DESIGN TOKENS & COMPONENT SPEC (v3, extracted 2026-07-09)

Source of truth: the four approved v3 mockups in
`docs/design-research/2026-07-09/pit-wall-console/`
(`s1-meta-snapshot.html`, `s2-matchup-matrix.html`, `s3-archetype-detail.html`,
`s-deck-viewer.html`). Every value below is copied verbatim from that code.
Where the four files drift slightly, the drift is documented and a canonical
value is chosen. **Build new pages from this file — you should not need to
open the v3 HTML.**

## 0. Non-negotiable project rules (apply to every page built from this spec)

- **Never invent domain facts.** Card names, leader/legend names, archetype
  names, event names come from grounding JSON files or data actually read.
  If grounding lacks something, use fewer real examples — never fabricated ones.
- **Riftbound:** NO hotlinking Riot CDN images (owner ToS decision). Riftbound
  card slots render as domain-colored placeholder frames with the card name.
- **One Piece:** only image URLs found in local grounding data; if none,
  color-framed placeholders.
- **MTG:** Scryfall image URLs from grounding data are fine to hotlink.
  Card images © Wizards of the Coast, served via Scryfall — credit in footer.
- **Every number** is either from grounding data (cite it in a provenance
  footnote, §5.10) or explicitly labeled `PLACEHOLDER`. Small-n winrates
  always show n and the credible interval. TopDeck-sourced views need a
  visible attribution slot with a link.
- **DSEG numerals NEVER get an "88" ghost underlay** — lit segments only.
- **Chart data-ink is always crisp vector** (anti-aliased SVG polylines/areas/
  bars). Retro flavor lives in FRAMING only: dashed grid plates, quantized
  ticks, pixel-font axis labels. No `image-rendering:pixelated`, no low-res
  canvas buffers, ever. Redaction (premium gates) is a wrapper over crisp
  vectors, never baked into the marks.
- **Mobile-first 390px AND a real ≥1100px widescreen layout** that uses the
  width (§7). `prefers-reduced-motion` fallbacks for all motion (§6.6).
- Freemium gates are presentation-only in mockups; production note carried in
  the code: *gate is server-side (entitlements module); free tier receives
  only the pre-quantized series, never the full payload.*

---

## 1. Color tokens

### 1.1 Core palette (canonical `:root`)

```css
:root{
  --bg:#0d0d12;          /* carbon black — page background, always */
  --panel:#14141a;       /* raised surface (cards, rows, tiles) */
  --panel2:#191921;      /* second-step surface (badges, chips, code plates) */
  --line:#2b2b35;        /* 1px hairline borders */
  --ink:#f2f2f7;         /* cool white — primary text */
  --dim:#8a8a96;         /* secondary text, labels, captions */
  --win:#3b9dff;         /* favorable WR — blue side of CVD-safe diverging scale */
  --loss:#ff7a1a;        /* unfavorable WR — orange side. NEVER red/green */
  --acc:#b45bff;         /* "sector purple" (F1) — best-in-class ONLY */
  --shadow:#000000;      /* hard 2px shadows */
  --chrome:linear-gradient(45deg,#999 5%,#fff 10%,#ccc 30%,#ddd 50%,#ccc 70%,#fff 80%,#999 95%);
}
```

Observed drift across the four v3 files (all acceptable; new pages use the
canonical values above, taken from the two newest files s3 + deck-viewer):

| token | s1 | s2 | s3 / deck-viewer (canonical) |
|---|---|---|---|
| panel  | `--bg2:#13131a` | `#14141b` / `--panel2:#1a1a23` | `#14141a` / `#191921` |
| line   | `#23232e` | `#26262e` | `#2b2b35` |
| dim    | `#8b8b99` | `#8e8e99` | `#8a8a96` |
| shadow | `#000` | `#050508` | `#000000` |
| accent var name | `--sector` | `--accent` | `--acc` |

### 1.2 Semantic roles

- `--win` (blue): favorable winrate (>52%), positive deltas `+x.x▲`, U-pips,
  curve bars, "favorable" spark strokes, unlock CTA gradient start.
- `--loss` (orange): unfavorable winrate (<48%), negative deltas `−x.x▼`,
  R-pips, sideboard pane chrome, price tiles, lit plaque stars, WIRE live-dot.
- `--acc` purple: **best-in-class only** — biggest mover, best matchup in a
  row, 1st-place chips, picked/selected states, PRO lock plates, focus rings.
  Scarcity is the point; never use it as generic decoration.
- Neutral band 48–52%: `--ink` / gray `#8a8a96`.
- WR threshold rule used everywhere (JS):
  `wr > 52 → win/blue · wr < 48 → loss/orange · else neutral`.
- Matrix heat fill (s2, exact formula — alpha capped for contrast):

```js
function cellBg(wr){
  const d=wr-50;
  if(Math.abs(d)<2) return 'rgba(242,242,247,.06)';           /* neutral 48–52 */
  const c = d>0 ? '59,157,255' : '255,122,26';
  /* alpha capped at .55: white 12px text stays >=4.5:1 on both scale extremes */
  const a = Math.min(.55, .12 + Math.abs(d)*.03);
  return 'rgba('+c+','+a+')';
}
```

### 1.3 Chart-framing grays (dimmer than data ink, brighter than bg)

- Dashed midlines / gridlines: `#262633` (s1), `#26262f`, `#22222b` (s2 hist)
- Tick marks: `#3a3a48` (s1/s3), `#2e2e38` (s2)
- 50%-reference dash: `#55555f` (s2), `#4a4a56` (s3)
- Chart plate backgrounds: `#0a0a0f` (s2), `#0f0f15` (s3/deck), `#1c1c26` (s1 badges/bars)
- Unlit plaque star / hollow text: `#3a3a48` / `#3a3a46`; hollow wordmark stroke `#2e2e3a`

### 1.4 MTG color-identity pips (s1, archetype-level)

```css
.pip{ width:9px;height:9px; border:1px solid #565664; border-radius:50% !important; }
.pip-W{background:#f8f6d8;}
.pip-U{background:#b9d4ec;}
.pip-B{background:#7d7673;border-color:#a6a1a0;}
.pip-R{background:#e49977;}
.pip-G{background:#a3c095;}
.pip-C{background:#8b8b99;border-radius:0 !important;transform:rotate(45deg);width:8px;height:8px;} /* colorless = gray diamond */
```

WUBRG order always; colorless renders one gray diamond. (Deck-viewer uses a
second, cost-level pip style: 13px squares with the symbol letter in
Press Start 2P 6px, `u`→`--win`, `r`→`--loss`, generic→`#8a8a96`, text color
`var(--bg)`.) These pip fills are the ONE sanctioned exception to the
diverging blue/orange rule — they encode game color identity, not performance.

**Canon note (2026-07-09):** the fills above are the canonical MTG pip set —
extension-spec §1.2 ("tokens 1.4 unchanged") governs MTG pips. The registry
`pipPalette` in `riftbound-games-ground.json` (extension-spec §1.4 "registry
verbatim") is canonical only for the NON-MTG pip systems it defines: One Piece
octagons and Riftbound domain plates. Pages must not restyle MTG pips from the
registry values.

---

## 2. Type stack

Google Fonts load: `JetBrains Mono` (400/700, s1 also 800), `Press Start 2P`,
`Archivo` variable (`wdth 62..125, wght 100..900`; s1 used `Archivo Narrow` 700).
DSEG7 via @font-face:

```css
/* DSEG7 Classic — SIL OFL. Self-host in production; CDN for mockup.
   NOTE: no "88:88" ghost underlay anywhere — lit segments only. */
@font-face{
  font-family:'DSEG7Classic';
  src:url('https://cdn.jsdelivr.net/npm/dseg@0.46.0/fonts/DSEG7-Classic/DSEG7Classic-Bold.woff2') format('woff2');
  font-weight:700; font-display:swap;
}
```

### 2.1 Roles

| role | stack | usage & sizes |
|---|---|---|
| **Data / body** | `'JetBrains Mono',monospace` | body 13px, `line-height:1.45`; table cells 11–13px; captions 9–11px. `font-variant-numeric:tabular-nums` set ON BODY so every number column aligns. `-webkit-font-smoothing:antialiased`. |
| **Chrome / badges** | `'Press Start 2P',monospace` | 7–10px only, `line-height:1`. Buttons, code badges, chips, WIRE badge, arrow buttons, axis NAMES (chart chrome is allowed; data marks are not). Never body copy — it's illegible past a few words. |
| **LED numerals** | `'DSEG7Classic','JetBrains Mono',monospace; font-weight:700` | Clocks 22px; stat tiles 24–32px; drilldown WR 34–44px; N readout 22px; gallery position 18px; group counts 12–13px; chart value labels 11px. Numbers only (DSEG has no letters). |
| **Display / wordmark** | `'Archivo',sans-serif` condensed | `font-weight:900; font-stretch:62%; font-variation-settings:'wdth' 62; text-transform:uppercase; letter-spacing:-.01em; line-height:.9–.95`. Page titles 40–64px, footer wordmark 46→72px. s1 variant: Archivo Narrow 700 + `transform:scaleY(1.25–1.5)` (compensate with margin `≈.46em`). |

### 2.2 DSEG rules

- **No ghost underlay.** Only the live value renders.
- Fixed-width live box so ticking values don't reflow the layout:

```css
.ghostwrap{ position:relative; display:inline-block; }   /* name is legacy; holds NO ghost */
.ghostwrap .live{ display:inline-block; text-align:right; }
#wrVal{ min-width:3ch; }   /* ch = DSEG digit cells; size to the widest value */
```

- Units (`%`, `$`, `TIX`, `MATCHES`) render in JetBrains Mono at ~40–50% of
  the DSEG size, `color:var(--dim)`, as a sibling `.unit` span — never in DSEG.
- Value color follows the semantic role of the metric (win=blue, price=orange,
  neutral=ink), applied to the `.lit` span.
- Label above value: 9–10px JetBrains Mono, `letter-spacing:.12em` (or 2px),
  `color:var(--dim)`, uppercase.

### 2.3 Micro-typography

- Section labels: 10px, `letter-spacing:.14em` (or 2px), dim, uppercase; the
  emphasized word wrapped in `b`/`.hd` at `color:var(--ink)`.
- Tickers: 11px, `letter-spacing:.04em`.
- Fine print/provenance: 9–10px dim, `letter-spacing:.06–.08em`, `line-height:1.7`.

---

## 3. Spacing, border & shadow grammar

### 3.1 Global reset — no rounded corners, ever

```css
*{ box-sizing:border-box; margin:0; padding:0; border-radius:0 !important; }
```

(Only exception: `.pip{border-radius:50% !important}` — the mana dot wins by
specificity.)

### 3.2 The panel formula

Every raised surface is the same three-part recipe:

```css
background:var(--panel);
border:1px solid var(--line);
box-shadow:2px 2px 0 0 var(--shadow);
```

1px hairlines everywhere; **hard offset 2px shadows, zero blur** — this is the
plate/console look. Larger set-pieces scale the shadow, never blur it:
gallery card scan `4px 4px 0 0`, peek/modal frame `4px 4px`–`6px 6px`.

### 3.3 Mechanical press state (signature interaction)

```css
.press{
  background:var(--panel);
  border:1px solid var(--line);
  box-shadow:2px 2px 0 0 var(--shadow);
  transform:translate(0,0);
  transition:transform 80ms steps(2,end), box-shadow 80ms steps(2,end);
  user-select:none;
  -webkit-tap-highlight-color:transparent;
}
.press:active{
  transform:translate(2px,2px);
  box-shadow:0 0 0 0 var(--shadow);
  transition:none;              /* instant press, 80ms stepped release */
}
```

The button physically sinks into its own shadow. Applies to: rows, format
tabs, sort switches, matrix cells, movers, chips, arrows — everything tappable.
Row-scale variant (dense lists): `.crow:active{transform:translate(1px,1px);}`.

- **On/selected state** inverts: `color:var(--bg); background:var(--ink); border-color:var(--ink);`
  (or stays pressed-in: `transform:translate(2px,2px); box-shadow:0 0 0 0` for
  latched toggles like the USD/TIX currency buttons).
- **Selected row/cell:** `border-color:var(--ink)` or
  `box-shadow:inset 0 0 0 2px var(--text), 2px 2px 0 0 var(--shadow);`
- **Focus:** `:focus-visible{ outline:2px solid var(--acc); outline-offset:2px; }`
  (offset `-2px` on full-bleed bars like the ticker).

### 3.4 Touch targets & rhythm

- 44px minimum touch height on primary controls (`min-height:44px`); 38px
  allowed on dense console switches; matrix columns stay narrow —
  **height carries the target** (`td.cell{height:44px}`, 58px on wide).
- Padding rhythm: panels `12px`, rows `8–9px 10px`, chips `5–6px 6–8px`,
  page gutter `12px` (390px), `16–32px` as width grows.
- Gaps: 6–8px between siblings, 8–12px between grid cells, 18px between sections.

### 3.5 Pixel garnish (desktop only)

Crosshair cursor, data-URI SVG, gated so touch never pays for it:

```css
@media (hover:hover) and (pointer:fine){
  body{cursor:url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="17" height="17"><g fill="%23f2f2f7"><rect x="7" y="0" width="3" height="6"/><rect x="7" y="11" width="3" height="6"/><rect x="0" y="7" width="6" height="3"/><rect x="11" y="7" width="6" height="3"/></g></svg>') 8 8, crosshair;}
  /* interactive elements: same crosshair with fill %23b45bff (purple) */
}
```

Pixel border-image frames for featured tiles (drilldown, selected deck):
URL-encoded SVG `border-image` with stepped corners — e.g. drill panel
`border:9px solid transparent; border-image:var(--pxframe) 9 stretch;`
(s1 uses a 6px/8×8 variant, s3 an 8px purple `repeat` variant for
`.deck.selected`). Reserve the border box up front
(`border:8px solid transparent; margin:-8px`) so selecting causes **zero reflow**.

Body texture (s1, optional): faint 45° carbon weave —
`repeating-linear-gradient(45deg, rgba(255,255,255,.012) 0 2px, transparent 2px 6px)` over `var(--bg)`.

---

## 4. Riso grain — the texture system

Grain = risograph ink speckle. **Accent only**: behind/beside content or over
LOCKED content — never over unlocked data marks. Three sanctioned recipes:

### 4.1 Colorless 1-bit speckle MASK (s1 — most flexible)

The tile is colorless; any gradient "prints through" it as grain via CSS mask:

```css
:root{
  /* feTurbulence crushed to 1-bit via discrete alpha transfer */
  --noise:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='48' height='48'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='1' seed='7'/%3E%3CfeColorMatrix values='0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0.6 0.6 0.6 0 -0.9'/%3E%3CfeComponentTransfer%3E%3CfeFuncA type='discrete' tableValues='0 0 0 1'/%3E%3C/feComponentTransfer%3E%3C/filter%3E%3Crect width='48' height='48' filter='url(%23n)'/%3E%3C/svg%3E");
}
.grain{
  position:absolute; inset:0; pointer-events:none;
  -webkit-mask-image:var(--noise); mask-image:var(--noise);
  -webkit-mask-size:64px 64px; mask-size:64px 64px;   /* 48px = denser, 96px = coarser */
}
/* then give each .grain instance its ink as a background gradient, e.g.: */
.movsec > .grain{ background:linear-gradient(180deg, rgba(180,91,255,.34), rgba(180,91,255,.10) 55%, transparent 92%); }
```

Signature use — the **WR-scale ramp** (header legend, doubles as the diverging-
scale key): blue plate fades right, orange plate fades left, purple prints
where they'd overlap:

```css
.riso-ramp{ position:relative; height:20px; border:1px solid var(--line); background:var(--panel); }
.riso-ramp .grain{
  background:
    linear-gradient(90deg,  var(--win)  0%, rgba(59,157,255,.25) 34%, transparent 46%),
    linear-gradient(270deg, var(--loss) 0%, rgba(255,122,26,.25) 34%, transparent 46%),
    linear-gradient(90deg,  transparent 34%, var(--acc) 50%, transparent 66%);
}
```

### 4.2 Dark multiply plates (s2 — grain + coarse "damaged print" blobs)

```css
:root{
  /* fine fractal grain: dark speckle plate; multiply over a gradient
     breaks the gradient into riso ink grain instead of gloss */
  --grain:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='140' height='140'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='2' stitchTiles='stitch'/%3E%3CfeColorMatrix type='matrix' values='0 0 0 0 0.04  0 0 0 0 0.04  0 0 0 0 0.06  0 0 0 0.55 0'/%3E%3C/filter%3E%3Crect width='140' height='140' filter='url(%23n)'/%3E%3C/svg%3E");
  /* coarse turbulence blobs for the premium misprint veil */
  --noiseC:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='56' height='56'%3E%3Cfilter id='m'%3E%3CfeTurbulence type='turbulence' baseFrequency='0.32' numOctaves='1' stitchTiles='stitch'/%3E%3CfeComponentTransfer%3E%3CfeFuncA type='discrete' tableValues='0 0 0 1 0 0'/%3E%3C/feComponentTransfer%3E%3CfeColorMatrix type='matrix' values='0 0 0 0 0.03  0 0 0 0 0.03  0 0 0 0 0.05  0 0 0 1 0'/%3E%3C/filter%3E%3Crect width='56' height='56' filter='url(%23m)'/%3E%3C/svg%3E");
}
/* footer divider: "where a competitor puts gloss, we put grain" */
.riso-divider{
  height:10px;
  background-image:var(--grain), linear-gradient(90deg, var(--win), var(--loss));
  background-blend-mode:multiply, normal;
  opacity:.55;
}
```

### 4.3 White overlay grain band (s3/deck — headers & CTA fills)

```css
:root{
  --grain:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='120' height='120'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='2' stitchTiles='stitch'/%3E%3CfeColorMatrix type='matrix' values='0 0 0 0 1  0 0 0 0 1  0 0 0 0 1  0 0 0 0.55 0'/%3E%3C/filter%3E%3Crect width='120' height='120' filter='url(%23n)'/%3E%3C/svg%3E");
}
.grainband{
  height:8px; position:relative; margin:0 0 14px;
  background-image:var(--grain), linear-gradient(90deg, var(--win), var(--acc));
  background-size:120px 120px, 100% 100%;
  background-blend-mode:overlay, normal;
}
.grainband::before{   /* 2px offset "misregistered second ink pass" */
  content:""; position:absolute; inset:0; transform:translate(2px,2px);
  background:linear-gradient(90deg, var(--acc), var(--win));
  opacity:.22; z-index:-1;
}
```

Also used as a 4px accent strip on panel tops (`.gallery::before`,
`.deck-head::before`) and as the fill of the unlock CTA button.

### 4.4 Duotone art band (deck-viewer hero)

Scryfall `img_art_crop` under three stacked overlays — art stays recognizable:

```css
.band .art{ filter:saturate(.72) contrast(1.08) brightness(.72); object-fit:cover; }
.band .tint{  /* blue shadows -> orange highlights */
  background:linear-gradient(112deg, rgba(59,157,255,.42) 0%, rgba(13,13,18,.05) 48%, rgba(255,122,26,.38) 100%);
  mix-blend-mode:hard-light;
}
.band .grain{ background-image:url(...fractalNoise 0.92 2oct, saturate 0...); background-size:140px 140px; mix-blend-mode:overlay; opacity:.55; }
.band .scrim{ background:linear-gradient(180deg, rgba(13,13,18,.15) 0%, rgba(13,13,18,.34) 55%, rgba(13,13,18,.88) 100%); }
```

Always include an art credit (`.band-credit`, 9px uppercase: `ART CROP: <CARD NAME>`).
Small inline card art (timing tower / list thumbs):
`filter:saturate(.78) contrast(1.05)` inside a 1px `--line` frame.

---

## 5. Component inventory

### 5.1 Wire ticker (results feed)

Full-bleed strip, top of every page. 30–44px tall (44px = touch-min pause
target). Structure: left `WIRE` badge (Press Start 2P 8px on `--acc` or
`--loss`), clipped scrolling track, right pause affordance.

```css
.ticker-track{ display:inline-flex; white-space:nowrap; will-change:transform;
  animation:tickscroll 42s linear infinite; }
@keyframes tickscroll{ to{ transform:translateX(-50%); } }
.ticker.paused .ticker-track{ animation-play-state:paused; }
```

Mechanics (all four files agree):
- Track content is **duplicated once**; `translateX(-50%)` = exactly one copy
  width → seamless loop. Any left-badge offset lives on a NON-animating clip
  wrapper, not the track (s1: `.ticker-clip{left:52px;right:36px;overflow:hidden}`).
- Speed pinned to **~35px/s** by JS: `duration = (track.scrollWidth/2)/35 + 's'`,
  recomputed after `document.fonts.ready` (font swap changes width).
- Tap / Enter / Space toggles pause (`role="button"` + `tabindex="0"` +
  `aria-pressed`, or `role="marquee" aria-live="off"`); pause glyph flips ❚❚/▶.
- Item colors: `.up{color:var(--win)} .dn{color:var(--loss)} .hot/.sec/.pu{color:var(--acc)}`.
- Content: only real results from grounding data (event · date · place ·
  player · archetype, deltas, sync line). Reduced motion: `animation:none`
  (static first items), hide the pause hint.
- Positioning: `position:fixed; top:0; height:30px` + `body{padding-top:30px}`
  (s2) or `position:sticky; top:0; z-index:50` (s3/deck).

### 5.2 Timing-tower row (ranked archetype list, s1)

An F1 timing screen: each row is one `<button class="row">` in a shared grid
with the header (`.thead` prints column captions at 9px dim).

```css
.thead,.row{ display:grid; grid-template-columns:20px 44px 1fr 120px 60px 46px; gap:8px; }
/* columns: P · ART+CODE · NAME/SHARE · 7D spark · WR·CI · Δ7D  */
.row{ align-items:center; background:var(--panel); border:1px solid var(--line);
  box-shadow:2px 2px 0 var(--shadow); padding:8px; margin-bottom:6px; font-size:13px; }
@media (max-width:479px){          /* 390px pattern: drop Δ7D, tighten */
  .thead,.row{grid-template-columns:16px 40px 1fr 120px 56px;gap:6px;}
}
@media (min-width:1100px){         /* wide: add N column, grow art/spark/bar */
  .thead,.row{grid-template-columns:26px 64px minmax(150px,1fr) 160px 76px 56px 52px;}
}
```

Cell anatomy:
- `P` position: JetBrains 800, dim; `P1` in ink. Re-sort fires a one-shot
  glitch on every `.pos`.
- ID cell: card art tile 30px tall (44px wide layout), `object-fit:cover`,
  desaturated frame (§4.4), stacked over a `CODE` badge — Press Start 2P 8px,
  centered, `background:#1c1c26; border:1px solid var(--line)`. Biggest mover
  gets `border-color/color:var(--acc)`.
- Name line: bold name with `overflow:hidden;text-overflow:ellipsis`
  (**must be `display:block`** — ellipsis is dead CSS on an inline span) +
  WUBRG pips. Share line: 56px (→140px wide) 6px bar
  (`.sharebar i{background:var(--txt)}` scaled to `share/maxShare`) + value.
- Spark: crisp SVG 120×36 (→160×48, 10:3 ratio preserved via viewBox).
  Framing: dashed midline `#262633 1px dasharray 1 3` + day ticks `#3a3a48`.
  Data: `stroke-width:2 round polyline` + `r=2.4` endpoint dot in the row's
  semantic color.
- WR cell: `.wr` 14px 800 in threshold color; CI **always** printed under it:
  `.ci{font-size:10px;color:var(--dim)}` as `±x.x`.
- N cell: in DOM at all widths, `display:none` until ≥1100px.
- Δ7D chip: `.delta{font-size:11px;700;padding:3px 4px;border:1px solid var(--line);background:#1c1c26;}`
  `+x.x▲` blue / `−x.x▼` orange / sector best = `color:var(--bg);background:var(--acc)`.
- Row is a disclosure toggle: `aria-expanded`, `.sel{border-color:var(--ink)}`;
  drilldown renders inline under the row on phones, into the right-rail dock ≥1100px.

### 5.3 DSEG stat tile (`.press.cell`)

```css
.cell{padding:12px 12px 10px; text-align:left;}          /* .press panel base */
.cell .lbl{font-size:10px; letter-spacing:.12em; color:var(--dim); text-transform:uppercase;
  display:flex; justify-content:space-between; gap:6px;}
.cell .seg{font-family:'DSEG7Classic','JetBrains Mono',monospace;
  font-size:30px; line-height:1.15; display:inline-block; margin-top:6px;}
.cell .unit{font-size:11px; color:var(--dim); font-family:'JetBrains Mono',monospace;}
.cell .sub{font-size:10px; color:var(--dim); margin-top:2px; display:block;}
.cell.win .lit{color:var(--win);}  .cell.price .lit{color:var(--loss);}
```

Grid: `1fr 1fr` on phones, `repeat(3or4,1fr)` ≥720px; `.cell.wide{grid-column:1/-1}`
for paired readouts (MAIN/SIDE counts). Values animate in with the quantized
roll-up (§6.1) via `data-target` / `data-dec` + IntersectionObserver.
Every tile's `.sub` states provenance or `PLACEHOLDER — NOT MEASURED`.

### 5.4 Console sort/filter switches (s1) & segmented period switch (s2/s3)

Mechanical console bar — same 2px press grammar, pixel type:

```css
.console{display:flex;align-items:center;gap:6px;overflow-x:auto;scrollbar-width:none;}
.sw{ font-family:var(--pix); font-size:8px; line-height:1;
  min-height:38px; padding:0 9px; display:inline-flex; align-items:center;
  color:var(--dim); background:var(--panel); border:1px solid var(--line);
  box-shadow:2px 2px 0 var(--shadow); transition:transform 80ms, box-shadow 80ms; }
.seg{display:inline-flex;} .seg .sw:not(:first-child){border-left-width:0;}   /* fused segment */
.sw:active{transform:translate(2px,2px);box-shadow:0 0 0 var(--shadow);transition:none;}
.sw.on{color:var(--bg);background:var(--ink);border-color:var(--ink);}         /* inverted = on */
.fpip{min-height:38px;min-width:34px;}  .fpip .pip{width:12px;height:12px;opacity:.35;}
.fpip.on{border-color:var(--ink);}      .fpip.on .pip{opacity:1;}
.con-count{font-size:9px;letter-spacing:1px;color:var(--acc);}                 /* "6/10 SHOWN", aria-live=polite */
```

Behavior contract: toggles carry `aria-pressed`; a `CLR` button appears
(`hidden` attr — note `.sw[hidden]{display:none}` must beat the author
`display:inline-flex`) only while filters are active; re-sort wipes the
roll-up cache so every readout re-rolls and P positions glitch once;
filter changes just collapse rows (no re-roll). Placement: h-scroll bar under
the format picker on phones; the SAME node reparented into the tower header
≥1100px (`flex-wrap:wrap;overflow:visible`) — listeners/state survive.
s2/s3 period pickers (`7D/30D/90D`) are the same `.press` segment with
`aria-pressed`, JetBrains 13px or Press Start 7px.

### 5.5 Star plaque (event grade) + league badge (s3)

Field-size grade, orange fill, **unlit segments stay visible — plaque, not ghost**:

```css
.plaque{ font-size:11px; letter-spacing:3px; white-space:nowrap;
  padding:3px 4px 3px 7px; border:1px solid var(--line); background:var(--panel2); line-height:1; }
.plaque .on{color:var(--loss);}   /* signal orange fill */
.plaque .off{color:#3a3a48;}      /* unlit segments stay visible */
.badge-league{ font-family:'Press Start 2P',monospace; font-size:7px;
  padding:5px 6px; border:1px solid #1f4e80; background:var(--panel2); color:var(--win); }
```

Scale (print it as a legend near first use):
`★ <32 · ★★ 32–63 · ★★★ 64–127 · ★★★★ 128–255 · ★★★★★ 256+ · LEAGUE = 5-0, size unreported`
League events get the blue `LEAGUE 5-0` badge, never stars. Plaque carries
`role="img" aria-label="event grade N of 5"` and a title with field size.
1st-place result chips upgrade to purple: `.first{color:var(--acc);border-color:var(--acc)}`.

### 5.6 Misprint-veil premium gate (s2 — canonical freemium treatment)

Data stays full-precision crisp vector; the FREE tier prints a riso veil over
it plus a defocus on a wrapper. Never pixelate, never fake the marks.

```css
.h-viz .data{ transition:filter 600ms steps(6,end); }
.h-viz.locked .data{ filter:blur(3.5px) saturate(.75); }
.riso-veil{
  position:absolute; inset:0; z-index:2;
  display:flex; align-items:center; justify-content:center;
  background-image:var(--noiseC), var(--grain),
    linear-gradient(105deg, rgba(59,157,255,.50), rgba(13,13,18,.30) 46%, rgba(255,122,26,.46));
  background-blend-mode:multiply, multiply, normal;
  clip-path:inset(0 0 0 0);
  transition:clip-path 700ms steps(12,end);   /* quantized squeegee wipe */
}
.h-viz.unlocked .riso-veil{ clip-path:inset(0 0 0 100%); pointer-events:none; }
.veil-chip{ font-family:'Press Start 2P',monospace; font-size:8px; padding:6px 8px 5px;
  background:rgba(13,13,18,.88); border:1px solid #3c3c46; letter-spacing:1px; } /* "PRO · LOCKED" */
```

Unlock = the veil wipes off left→right in 12 discrete steps while the defocus
steps away. Variants:
- **s1 grain plate + quantized blur** on mover charts: wrapper custom props
  `--lockblur:4px / --lockgrain:.9` → unlock ticks through
  `[3.5,3,2.5,2,1.5,1,.5,0]` at 90ms; exact deltas masked as `+?.?▲` while locked.
- **s3 resolution gate**: 90D series bucket-averaged (`quantize(arr,8,...)`)
  under a lockveil chip `90D · 1/8 RES — PRO`; unlock coarse-steps factor
  8→1 at 110ms — *literal* full resolution restore. Unlock CTA is the
  grain-gradient button (§4.3).
- Mock-only caveat carried in code comments: production gate is server-side;
  true values never reach the free-tier DOM.

### 5.7 Card inspector dock + hover float + tap modal (deck-viewer)

Three-tier card preview, chosen by capability:
1. **≥1100px:** permanent third column (`320px`, `position:sticky; top:48px`)
   — "CARD INSPECTOR" panel: framed `img_normal`, Press-Start name (8px),
   type + pips meta, price detail in both currencies (current one highlighted
   `.cur` ink / `.oth` dim). Hovering any list row renders INTO the dock (no float).
2. **Fine pointer below 1100px:** floating preview `#hoverPrev` (244px image,
   `position:fixed; pointer-events:none`, flips side near the right edge,
   clamped vertically), gated `@media (hover:hover) and (pointer:fine)`.
3. **All inputs:** tap modal — `rgba(13,13,18,.86)` backdrop, framed image
   `max-width:min(84vw,336px)`, name plate, price plate, `TAP ANYWHERE TO CLOSE`,
   Escape closes, focus returns to the source row. `role="dialog" aria-modal="true"`.

List row anatomy (`.crow`): DSEG count (blue main / orange sideboard) ·
34×24 art thumb · ellipsized name · cost pips · right-aligned row price
(`COUNT × UNIT`, legend in the section header). Hover/focus tints name+thumb
to the pane's ink. Sideboard is a **distinct orange pane**: `border:1px solid var(--loss)`,
header strip `SIDEBOARD · n / 15 SLOTS`, orange counts.

### 5.8 Drilldown / picked-game tile (s1/s2)

Pixel border-image frame (§3.5) + riso corner wash + DSEG readouts:
WR% at 34–44px in threshold color, SAMPLE N at 22px, `CI 95% ± x.x` line with
a CI bar (band spanning the interval on a 30–70 scale, midline, colored point
marker), trend chip `▲ +x.x`/`▼ −x.x` + 12-week sparkline with dashed 50% rule
(`stroke-dasharray:3 3`) and week ticks. On phones it renders inline (s1) or
as a fixed section that `scrollIntoView({block:'nearest'})`s on selection (s2);
≥1100px it docks into the sticky right rail. `aria-live="polite"`.

### 5.9 Matchup matrix (s2)

`table-layout:fixed; border-collapse:separate; border-spacing:2px` — never
overflows horizontally. Sticky column heads under ticker+controls
(`top:86px = 30px ticker + 56px sticky controls`). Each cell is a `.cellbtn`
(§3.3 press physics) with heat fill from `cellBg()` (§1.2). Best matchup in a
row = 7×7px purple corner tab (`.best::after`). Low sample encodes **in the
grid**, not just the drilldown:

```css
.cellbtn.lown::before{ content:''; position:absolute; inset:0; pointer-events:none;
  background:repeating-linear-gradient(45deg, rgba(13,13,18,.45) 0 3px, transparent 3px 8px); }
/* legend: HATCH = LOW SAMPLE N<50 */
```

Mirror diagonal: `—` on `#111117`. Wide (≥1100px): cells 44→58px, gain in-cell
`N### ▲+x.x` sub-line and full archetype names in row heads (both
`display:none` below). Cell `aria-label` spells out names, %, low-sample, N.

### 5.10 Provenance footnote (every page, every data zone)

9–10px, dim, uppercase, `letter-spacing:.06–.08em`, `line-height:1.7`. States:
data window, N (decks/events), source, snapshot date, and what is placeholder.
Real examples from the mocks (pattern to copy):

- `COLORS: PIP-MINED FROM APR–JUN 2024 MTGO MAINBOARDS (COLOR COUNTS AT ≥10% OF PIPS) · REP CARDS: NAMESAKE PICKS — MTGOFORMATDATA RULE-FILE PORT PENDING`
- `PRICE = MEAN OVER DECKS WITH COMPLETE PRICE DATA: N=165 (USD) · N=388 (TIX) OF 717 · SCRYFALL 2026-07-08 SNAPSHOT, ONE CANONICAL PRINTING PER CARD`
- `MOCKUP · PLACEHOLDER DATA · NOT MEASURED FROM REAL EVENTS`
- Deck-viewer fine print ends: `CARD IMAGES © WIZARDS OF THE COAST, SERVED VIA SCRYFALL`

TopDeck-sourced views: add a visible attribution slot with link in this
footnote position. Footer block: riso divider/grainband + condensed wordmark
(second line hollow or `#3a3a46`) + the fine print.

### 5.11 Other established components (brief)

- **Format picker** `.fmt`: Press Start 8px, 44px-min press chips, h-scroll,
  `.on` inverted.
- **PRO chip**: chrome gradient. At 8px pixel type a gradient TEXT fill reads
  flat — s1 carries chrome on a 2px border frame
  (`.pro{padding:2px;background:var(--chrome)} .pro i{padding:6px 8px;background:#1a1a22}`);
  s2 uses `background-clip:text` on larger chips. Either is sanctioned.
- **Staples gallery** (s3): one big `img_normal` scan (`aspect-ratio:488/680`,
  `max-width:300px`, `box-shadow:4px 4px`), press arrows (44×88px min) + swipe
  (40px threshold) + arrow keys, DSEG `01 / 12` position, stats row
  (IN-% + bar, AVG COPIES, PRICE), 34px thumb rail (`aria-current` +
  `scrollIntoView`), 5s auto-cycle held on hover/focus/modal/hidden tab,
  killed under RM (`AUTO-CYCLE OFF · REDUCED MOTION`). Adjacent scans
  pre-warmed via `new Image()`; thumbs beyond the first 4 `loading="lazy"`.
  Basic lands filtered by `type_line` (data), never name-memory.
- **Mana curve** (deck-viewer): crisp SVG bars `shape-rendering:crispEdges`
  fill `--win`, zero-buckets 2px stub `#2b2b35`, dashed gridlines every 5,
  Press-Start x-labels (chrome), DSEG value labels; caption discloses
  charted/excluded counts computed from the list.
- **Deck feed rows / notable rows** (s3): grid `44px 1fr auto` — date block,
  event+player middle (ellipsized), result chip + star plaque right. Rows with
  embedded lists expand inline (`aria-expanded`, caret `▸ TAP FOR 75` →
  `▾ 75 ON DECK`, purple pixel frame on selected); rows without deep-link out
  with `↗` (`target="_blank" rel="noopener"`).
- **Copy/export bar**: `⧉ COPY DECKLIST` uses clipboard API + textarea
  fallback, flips to `✓ COPIED — 75 CARDS` for 1.8s with a glitch.
- **Unlock bar** (s1): panel + purple grain plate + `.btn-unlock` (pixel type,
  `border:1px solid var(--acc)`).

---

## 6. Motion grammar

Everything mechanical, quantized, event-driven. Nothing loops except the ticker.

### 6.1 Quantized arcade roll-up (numbers)

**8 discrete ticks, 480–600ms total, snap exact on the last tick.** No easing
curves — the quantization IS the aesthetic.

```js
function rollup(el, target, dec){
  if(RM){ el.textContent = fmtVal(target,dec); return; }        // reduced motion: jump
  const TICKS=8, DUR=600, start=parseFloat((el.textContent||'0').replace(/,/g,''))||0;
  let i=0;
  clearInterval(el._roll);
  el._roll=setInterval(()=>{
    i++;
    const v = start + (target-start)*(i/TICKS);
    el.textContent = (i>=TICKS) ? fmtVal(target,dec) : v.toFixed(dec);
    if(i>=TICKS) clearInterval(el._roll);
  }, DUR/TICKS);
}
```

Gates: `prefers-reduced-motion` AND on-screen only — IntersectionObserver
(threshold .1–.4) with a synchronous `getBoundingClientRect` fallback for
freshly rendered / hidden-pane elements (IO and native lazy never fire when
`visibilityState:hidden`; promote in-viewport work manually). Roll-ups re-fire
on data change, sort change (cache wiped per format), currency toggle, tab
switch — value changes are diffed against a `shown{}` cache so only changed
cells animate.

### 6.2 `steps()` timing everywhere

CSS transitions/animations use step functions, never smooth curves:

| use | timing |
|---|---|
| press release | `transform 80ms steps(2,end), box-shadow 80ms steps(2,end)` (press itself `transition:none`) |
| glitch | `200–240ms steps(2,end)` or `steps(2,jump-none)`, iteration count `1` |
| veil squeegee wipe | `clip-path 700ms steps(12,end)` |
| lock defocus | `filter 600ms steps(6,end)` |
| label fade-in | `opacity 300ms steps(3,end)` |
| gallery stat bar | `width 200ms steps(4,end)` |
| JS step sequences | blur lift 8 steps @90ms · res restore 8 steps @110ms |

### 6.3 One-shot RGB-split glitch

Fired on CHANGED cells/events only. Never loops, never ambient.

```css
@keyframes glitch{
  0%  {clip-path:inset(0 0 52% 0); transform:translate(-2px,0); text-shadow:2px 0 var(--win), -2px 0 var(--loss);}
  50% {clip-path:inset(46% 0 0 0); transform:translate(2px,0);  text-shadow:-2px 0 var(--win), 2px 0 var(--loss);}
  100%{clip-path:none; transform:none; text-shadow:none;}
}
.glitch{animation:glitch 240ms steps(2,jump-none) 1;}
```

```js
function glitch(el){
  if(RM) return;
  el.classList.remove('glitch'); void el.offsetWidth;   // restart trick
  el.classList.add('glitch');
  el.addEventListener('animationend',()=>el.classList.remove('glitch'),{once:true});
}
```

Triggers observed: value changed after a data refresh / period switch;
positions after re-sort; gallery card name on advance; chart title on range
change; unlock button when a locked chart is poked; copy-button confirmation.

### 6.4 Ticker
Linear infinite, ~35px/s (§5.1). The only looping animation in the system.

### 6.5 Unlock choreography
"The upgrade animation IS the mechanic": premium reveals run the same
quantized 8–12 step cadence as the roll-ups (blur 4px→0, veil wipe, resolution
factor 8→1). Reduced motion: instant state change, no sequence.

### 6.6 Reduced-motion contract (required block on every page)

```css
@media (prefers-reduced-motion:reduce){
  .ticker-track{animation:none;}     /* static first-N items */
  .glitch{animation:none;}
  .press, .press:active{transition:none;}
  /* + veil/defocus/label transitions:none; gallery auto-cycle killed in JS */
}
```

JS side: `const RM = matchMedia('(prefers-reduced-motion: reduce)').matches;`
checked in `rollup`, `glitch`, auto-cycle arm, unlock sequences, smooth-scroll
(`behavior:RM?'auto':'smooth'`), and the s2 clock colon blink
(`(REDUCED || sec%2===0) ? ':' : ' '` — colon stays solid under RM).

---

## 7. Layout grammar

### 7.1 Mobile-first (390px is the approved layout — never regress it)

- Single centered column: `.wrap{max-width:680px; margin:0 auto; padding:0 12px;}`
  (observed caps 620/720/680; canonical 680). Base font 13px.
- Everything stacks; wide-only elements exist in the DOM but are
  `display:none` (tower N column, in-cell matrix subs, extra axis ticks via
  `.wideonly{display:none}`).
- Horizontal overflow is handled by h-scroll strips with hidden scrollbars
  (`overflow-x:auto; scrollbar-width:none; ::-webkit-scrollbar{display:none}`),
  optionally `scroll-snap-type:x mandatory` (movers carousel, thumb rail,
  format picker, console).
- <480px: the timing tower drops the Δ7D column (`display:none` on
  `.h-delta`/`.dcell`) and tightens fixed columns — the NAME column keeps
  usable width; the delta stays reachable in movers + drilldown.
- Tables never scroll sideways: `table-layout:fixed` grids (matrix) — height
  carries touch targets, not width.
- Sticky stack budget (s2): ticker `top:0` (30px) → controls
  `position:sticky; top:30px` (56px) → matrix column heads
  `position:sticky; top:86px`. Keep this arithmetic when composing new sticky layers.

### 7.2 Mid widths
`≥600–768px`: type scale up (wordmark 46→72px, titles 40→56–58px), hero grid
`1fr 1fr`→`repeat(3-4,1fr)`, decklist `column-count:2` ≥480px, `.wrap` widens.
s1 goes fully fluid at 640px (`max-width:none`) so laptops have no dead gutters.

### 7.3 ≥1100px — the pit-wall spread (the shared breakpoint everywhere)

`matchMedia('(min-width:1100px)')` is THE widescreen constant in all four
files. Each page becomes a multi-zone console; ticker/header/footer run full
width; ultra-wide is capped (`max-width:1440–1720px`).

Patterns to reuse:
- **Main + sticky instrument rail** (s1/s2):
  `grid-template-columns:minmax(0,1fr) 400px` (s1, `column-gap:20px`) or flex
  main + `.dock{flex:0 0 clamp(360px,30vw,430px); position:sticky; top:38px;}`
  (s2). Rail: `position:sticky; top:0; max-height:100dvh; overflow-y:auto;
  scrollbar-width:none; border-left:1px solid var(--line);` Drilldown docks on
  top of the rail (`order:-1`) so tapped telemetry is immediately visible.
- **Named-area bench grid** (s3):
  `grid-template-columns:minmax(0,1.15fr) minmax(0,1fr); column-gap:32px;`
  with `grid-template-areas` `"top top" / "title chips" / "band band" /
  "hero hero" / "gpair gpair" / "latest right" / "foot foot"`; gallery 40% /
  notable 60% share one row (`minmax(0,2fr) minmax(0,3fr)`).
- **Three-zone console** (deck-viewer):
  `grid-template-columns:minmax(0,1fr) 340px 320px; column-gap:22px;` areas
  `"export hero dock" / "main hero dock" / "main rail dock"`; inspector dock
  is the permanent third column (`.docksticky{position:sticky;top:48px}`).
  `≥1360px` the mainboard flows `column-count:2; column-rule:1px solid var(--line)`.
- Components EARN their width: bigger art tiles (30→44px), longer sparks
  (120→160px), longer share bars (56→140px), extra columns (N), in-cell N +
  trend, full archetype names, more axis ticks — never just stretched whitespace.

### 7.4 DOM reparenting pattern (breakpoint-crossing state)

When a component moves between mobile and wide homes (console → tower header,
drill → dock, history → rail), reparent the SAME node so listeners and state
(unlock, selection) survive, and restore the exact mobile DOM order below the
breakpoint:

```js
const wideMQ = matchMedia('(min-width:1100px)');
let wideApplied = null;                 // idempotence guard — resize fires often
function layoutWide(){
  const w = wideMQ.matches;
  if (w === wideApplied) return;
  wideApplied = w;
  if (w){ /* append nodes into .main-col / .dock */ }
  else  { /* re-insert nodes in original mobile order */ }
}
layoutWide();
wideMQ.addEventListener('change', layoutWide);
window.addEventListener('resize', layoutWide);   // fallback: some embedded
// viewports resize without dispatching matchMedia change events
```

### 7.5 Image loading policy

`loading="lazy" decoding="async"` on list art; BUT embedded/hidden preview
panes report `visibilityState:hidden` where native lazy + IO never fire —
promote images within 200px of the viewport to `loading="eager"` via a
rect-check on scroll (s1 `loadArtInView()`). Carousels: current image live,
adjacent pre-warmed with `new Image().src`, first 4 thumbs eager.

---

## 8. Data-honesty display rules (enforced by the design system)

- WR always prints with its CI (`54.2 ±1.4`) or a CI bar; N is a first-class
  column/readout, not a tooltip.
- Low sample is encoded in the visualization itself (hatch overlay, N<50
  legend entry), with the threshold stated.
- Deltas print sign + glyph (`+2.3▲` / `−1.2▼`) in the diverging inks.
- Diverging scale is blue/orange (CVD-safe), **never red/green**; purple is
  reserved for best-in-class.
- Totals shown are computed from the displayed list at render time
  (deck price = Σ count×unit), never hardcoded; the tile sub-line says
  `— COMPUTED FROM LIST`.
- Placeholder series are labeled on-chart, in the readout, and in the footer
  (`PLACEHOLDER SERIES`, `NOT MEASURED`).
- One measure per chart pane — dual series get stacked panes (s2 history: WR
  line pane over weekly-N column pane), not dual axes on one pane. (The s3
  share/WR strip with twin y-axes is the grandfathered exception; prefer panes.)
- Free tier masks values (`+?.?▲`, quantized series), it never shows wrong ones.
