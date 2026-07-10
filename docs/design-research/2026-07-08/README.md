# MetaSurf Visual Direction — Overnight Design-Research Report

**Date:** 2026-07-08
**Audience:** MetaSurf owner, picking a visual direction
**Inputs:** ~50 researched techniques across 6 angles (dithering, pixel-UI, terminal/CRT, retro-motion, dataviz-identity, brutalist/award, type-color); 3 full directions; 9 HTML mockups (S1 meta snapshot, S2 matchup matrix, S3 archetype detail per direction), each critiqued on 4 dimensions (identity / data legibility / mobile-390px / persona fit, 0–10) and then revised against the critique.

---

## Recommendation

**Prototype the Pit-Wall Console for real. Keep Overprint Bulletin alive as the light-mode / report-export identity. Fold Grinder Terminal's honesty furniture into whichever direction ships.**

### Ranking

| Rank | Direction | Identity | Data legibility | Mobile | Persona fit | Total (of 120) |
|---|---|---|---|---|---|---|
| 1 | **Pit-Wall Console** | 8.3 | **6.7** | **7.0** | 7.7 | **89** |
| 2 | **Overprint Bulletin** | 7.7 | 6.0 | 7.0 | **8.3** | 86 |
| 3 | **Grinder Terminal** | 8.0 | 5.7 | 6.3 | 8.0 | 84 |

(Averages across the three screens; totals sum all 12 critique scores.)

Why Pit-Wall wins: it posted the single best screen of the night (S2 matrix: 9/8/8/8) and it is the only direction where the critique scores *data legibility* and *mobile* — the two dimensions a grinder actually lives in — at or above 6.5 average. Its weaknesses (motion discipline, freemium leaks) are engineering problems with known fixes; the other two directions' weaknesses are closer to identity-versus-legibility tradeoffs.

Honest caveat on the whole exercise: **no direction scored above 8 on data legibility on any screen except Pit-Wall's S2.** All three identities tax legibility somewhere — pixel fonts at small sizes, halftone plates behind digits, LED numerals. The real prototype must treat legibility regressions as blockers, not polish items.

A second caveat on scores: each mockup went through critique → revision. The revision notes claim the listed must-fixes were applied and verified (several in headless Chromium at 390px); the scores shown are the critique's and were not re-issued after revision, so treat them as a floor, and spot-check the revised files yourself.

---

## 1. Pit-Wall Console — `pit-wall-console`

**Concept.** MetaSurf as race-ops hardware: F1 timing tower crossed with an arcade scoreboard. S1 is a ranked timing tower (position, 4-char archetype code, share bar, delta chip; purple reserved for best-in-class movers, exactly as F1 uses purple sectors). S2 drilldowns read out on DSEG seven-segment numerals. The defining trait is that it MOVES and it's TACTILE: quantized arcade roll-ups, single glitch frames on data refresh, a results wire-feed ticker, and every tappable element mechanically depressing 2px. Maximal contrast with untapped.gg's soft hover glows; the most esports-broadcast, screenshot-viral direction. Palette is carbon black / cool white with a CVD-safe blue-orange diverging winrate scale (deliberately not red-green).

**Mockups**

| Screen | File | Identity | Legibility | Mobile | Persona |
|---|---|---|---|---|---|
| S1 Meta Snapshot | [pit-wall-console/s1-meta-snapshot.html](pit-wall-console/s1-meta-snapshot.html) | 8 | 6 | 6 | 8 |
| S2 Matchup Matrix | [pit-wall-console/s2-matchup-matrix.html](pit-wall-console/s2-matchup-matrix.html) | **9** | **8** | **8** | 8 |
| S3 Archetype Detail | [pit-wall-console/s3-archetype-detail.html](pit-wall-console/s3-archetype-detail.html) | 8 | 6 | 7 | 7 |

**Signature techniques (with research sources)**

- F1 live-timing-tower layout — https://f1-dash.com/ , https://github.com/pesaventofilippo/f1dash
- DSEG 7-segment LED font for hero numerals (SIL OFL) — https://www.keshikan.net/fonts-e.html , https://github.com/keshikan/DSEG
- Quantized number roll-ups (CountUp.js pattern, steps easing) — https://github.com/inorganik/countUp.js/
- Event-driven clip-path glitch with steps() timing + RGB split — https://alvarotrigo.com/fullPage/css-glitch-effect/
- CSS-only duplicate-track ticker at ~35px/s — https://motion.dev/magazine/building-the-ultimate-ticker , https://www.smashingmagazine.com/2024/04/infinite-scrolling-logos-html-css/
- Chunky :active press physics + pixel cursor garnish — https://developer.mozilla.org/en-US/docs/Web/CSS/cursor , https://auroratide.com/posts/pixelart-and-the-image-rendering-paradox/
- Stepped pixel-border chrome (SVG border-image) — https://nigelotoole.github.io/pixel-borders/
- Tiny-canvas staircase sparklines + image-rendering:pixelated — https://developer.mozilla.org/en-US/docs/Games/Techniques/Crisp_pixel_art_look
- Dither-degradation freemium (pixel-size 8→1 unlock) — https://developer.mozilla.org/en-US/docs/Web/CSS/image-rendering , https://css-tricks.com/keep-pixelated-images-pixelated-as-they-scale/
- Pure-CSS Y2K chrome PRO badge — https://ibelick.com/blog/creating-metallic-effect-with-css ; blue-orange diverging scale — https://www.datylon.com/blog/data-visualization-for-colorblind-readers , https://colorbrewer2.org/
- Prediction-market probability display patterns — https://avark.agency/learn/prediction-market-design-patterns
- Monospace-brutalist indexing + oversized wordmark — https://basement.studio/
- Matchup-matrix precedents to beat (provenance line, share-sorted axes) — https://www.vicioussyndicate.com/drr/matchup-chart-data-reaper-report/ , https://www.metamages.com/sessions/8532707e-04a5-40da-9eca-e96b67f2e21d
- No-motion-first / reduced-motion architecture — https://web.dev/articles/prefers-reduced-motion , https://www.tatianamac.com/posts/prefers-reduced-motion

**What the critique found (honest)**

- The freemium tease originally leaked its payload (mover codes and exact deltas visible free; only chart shape pixelated) — revision masks deltas as `+?.?▲`, but the deeper pattern problem stands for all three directions: **client-side occlusion is not a gate.** Production must server-gate via the entitlements module; the mockups only document this in comments.
- Touch targets repeatedly came in under 44px (format pills 26px, ticker 28px, matrix cells 38px) and had to be fixed in revision — density and thumb ergonomics are in real tension in this direction.
- Ticker speed drifted from spec (~42px/s vs 35) and had to be re-measured after webfont load; motion here has many small correctness details, and the direction carries the strictest reduced-motion obligations of the three.
- S1 and S3 legibility is only 6: LED numerals are display-only by design, and the spec's CountUp.js was replaced by a hand-rolled equivalent (documented deviation, but a decision to make deliberately).
- Some spec moments (8→1 unlock tween, wire-refresh glitch) only exist because revision added simulated demo hooks — the real-data plumbing is unbuilt.

---

## 2. Overprint Bulletin — `overprint-bulletin`

**Concept.** A risograph-printed tournament bulletin taped to the GP wall, rebuilt as a *light-mode* web app: warm paper, two overprinted spot inks (Fluoro Pink #FF48B0 + Teal #00838A, overlap plum as the free third color), halftone dots doing the actual data encoding — dot density IS the winrate, which the research confirms no chart library or competitor has touched. Card art Atkinson-dithered once at build time and tinted per color identity via CSS multiply blend (~1–2KB per image). Built for bright venue halls at noon; nearly everything is zero-JS CSS.

**Mockups**

| Screen | File | Identity | Legibility | Mobile | Persona |
|---|---|---|---|---|---|
| S1 Meta Snapshot | [overprint-bulletin/s1-meta-snapshot.html](overprint-bulletin/s1-meta-snapshot.html) | 8 | 6 | 6 | 8 |
| S2 Matchup Matrix | [overprint-bulletin/s2-matchup-matrix.html](overprint-bulletin/s2-matchup-matrix.html) | 7 | 7 | 8 | **9** |
| S3 Archetype Detail | [overprint-bulletin/s3-archetype-detail.html](overprint-bulletin/s3-archetype-detail.html) | 8 | **5** | 7 | 7 |

(Note the S3 file lives in a different folder than S1/S2 — an artifact of the overnight run worth consolidating.)

**Signature techniques (with research sources)**

- Risograph 2-color overprint identity + mix-blend-mode overlap — https://github.com/mattdesl/riso-colors , https://stencil.wiki/wiki/Category:Riso_inks
- Pure CSS halftone in 3 declarations (radial-gradient dots + gradient map + contrast()) — https://frontendmasters.com/blog/pure-css-halftone-effect-in-3-declarations/ , https://css-irl.info/css-halftone-patterns/ , https://codepen.io/thebabydino/pen/dyoPdqj
- Cluster-dot halftone + duotone mapping for charts (the open data-viz lane) — https://maximmcnair.com/p/webgl-dithering
- Atkinson / error-diffusion dithering at build time — https://surma.dev/things/ditherpunk/ , https://www.npmjs.com/package/canvas-dither
- Low-tech Magazine pattern: dithered images + blend-mode tinting — https://solar.lowtechmagazine.com/about/the-solar-website/
- Grainy gradients (feTurbulence + contrast squash) — https://css-tricks.com/grainy-gradients/
- Dither-degradation freemium teasers — https://developer.mozilla.org/en-US/docs/Web/CSS/image-rendering
- GitHub-contribution-graph quantized steps for small cells — https://github.com/kevinsqi/react-calendar-heatmap
- Warm 'calm hardware' light palette counterweight — https://daylightcomputer.com/
- Silkscreen pixel micro-badges at native 8px grid — https://fonts.google.com/specimen/Silkscreen
- IBM Plex Mono data-table workhorse — https://fonts.google.com/specimen/IBM%2BPlex%2BMono
- Halftone hover/tap reveals (locked = halftone, premium = full art) — https://leanrada.com/notes/pure-css-halftone/ , https://speckyboy.com/combining-halftone-effects-with-code/
- Trend validation: dithering as active 2025–26 award-circuit aesthetic — https://onepagelove.com/tag/dither-effect , https://www.awwwards.com/sites/type-dither

**What the critique found (honest)**

- **The brand's #1 technique was barely visible on its own homepage:** at S1 scale the halftone read as flat tint until revision added a full-row coarse dot plate. On S3 the true contrast-crush recipe originally only appeared in one meter. The identity depends on halftone being *seen*, and that requires deliberate large surfaces per screen — it does not fall out for free.
- **S3 legibility is the worst single score of the night (5):** halftone dots bled under 10px `n=` text, the misregistration ghost was confusable with the 50% reference line, and decklists led with zero-information 4-of cores. All patched, but the pattern — ink texture fighting small numerals — is intrinsic to the direction.
- The image system is still vaporware: every "dithered card art" surface is a runtime procedural placeholder. The real build-time Atkinson PNG-8 pipeline (linear-space luminance) doesn't exist yet, and heavily-dithered card art still needs an **owner ToS review** before it's assumed shippable.
- Fluoro pink fails text contrast on paper (~2.6:1); the direction now runs a dual-token system (fluoro for plates/fills, darkened `--pink-ink`/`--teal-ink` for read matter) that every future component must respect.
- Freemium ghost canvases carried true premium values in free-tier DOM (`data-pts`) — same server-side gating requirement as Pit-Wall.

---

## 3. Grinder Terminal — `grinder-terminal`

**Concept.** The Bloomberg terminal of the metagame: an instrument you boot the night before a Challenge. Strict character grid (Monospace Web pattern), amber-on-near-black, box-drawing furniture, datasheet faceplate header advertising the statistical rigor (`MS-01 // META SNAPSHOT · WINDOW: 14D · N=4,213`), text-glyph sparklines (▁▂▃▄▅▆▇█) that copy-paste into Discord meta arguments. Cheapest to build (almost zero effects layer) and hardest to mistake for any competitor.

**Mockups**

| Screen | File | Identity | Legibility | Mobile | Persona |
|---|---|---|---|---|---|
| S1 Meta Snapshot | [grinder-terminal/s1-meta-snapshot.html](grinder-terminal/s1-meta-snapshot.html) | 8 | 6 | **5** | 7 |
| S2 Matchup Matrix | [grinder-terminal/s2-matchup-matrix.html](grinder-terminal/s2-matchup-matrix.html) | 8 | 5 | 7 | 8 |
| S3 Archetype Detail | [grinder-terminal/s3-archetype-detail.html](grinder-terminal/s3-archetype-detail.html) | 8 | 6 | 7 | **9** |

**Signature techniques (with research sources)**

- Character-grid layout ('The Monospace Web') — https://owickstrom.github.io/the-monospace-web/ , https://wickstrom.tech/2024-09-26-how-i-built-the-monospace-web.html
- Bloomberg amber-on-black density doctrine — https://news.ycombinator.com/item?id=19153875 , https://www.bloomberg.com/company/stories/how-bloomberg-terminal-ux-designers-conceal-complexity/
- Unicode block-character sparklines — https://rosettacode.org/wiki/Sparkline_in_unicode , https://blog.jonudell.net/2021/08/05/the-tao-of-unicode-sparklines/
- Departure Mono identity font (SIL OFL, 11px grid) — https://departuremono.com/ , https://github.com/rektdeckard/departure-mono
- IBM Plex Mono table workhorse — https://fonts.google.com/specimen/IBM%2BPlex%2BMono
- Terminal-brand chrome: bracketed nav, boot/loading lines, line-number gutter — https://www.terminal.shop/ , https://charm.land/blog/terminaldotshop/
- Retro-OS boot metaphor with instrument discipline — https://poolsuite.net/ , https://teenage.engineering/designs
- Industrial-datasheet labeling system — https://usgraphics.com/products/berkeley-mono , https://neil.computer/notes/introducing-berkeley-mono/
- Dual-phosphor semantics (green signal / amber caution) — https://en.wikipedia.org/wiki/Monochrome_monitor
- Pure-CSS CRT scanlines as seasoning — https://aleclownes.com/2017/02/01/crt-display.html , https://dev.to/ekeijl/retro-crt-terminal-screen-in-css-js-4afh
- Bayer-dither scramble instead of gaussian blur for gating — https://blog.maximeheckel.com/posts/the-art-of-dithering-and-retro-shading-web/
- Mobile-dense-table doctrine — https://www.pencilandpaper.io/articles/ux-pattern-analysis-enterprise-data-tables
- No-motion-first architecture — https://www.tatianamac.com/posts/prefers-reduced-motion

**What the critique found (honest)**

- **Mobile is the weak flank (S1 scored 5):** the 10ch WR track overflowed at 390px, touch targets sat at line-height, the format picker hid off-screen items with no affordance, and long archetype names clipped silently. All were fixed in revision, but the character grid genuinely fights 390px — every column is a hand-negotiated budget.
- **The honesty brand caught its own mockups lying:** a blinking LIVE cursor next to 4-hour-stale data, a fabricated "ok 0.31s" latency readout, and a boot line contradicting the legend's n<30 threshold. Revision wired these to real values (ingest-tied SYNCED label, measured `performance.now()`), which is exactly the discipline this direction demands forever — fake telemetry is fatal to it.
- Display-font rules are fragile: VT323 below 16px corrupted 3-letter codes on S2; block glyphs (▁–█, ▲▼) need an explicitly pinned glyph-capable fallback stack and U+FE0E or iOS renders emoji. The type system now has hard rules (Departure/VT323 ≥16px only, `--glyph-stack` pinned) that must be enforced in code review.
- S2 legibility is only 5 even after fixes — amber-dim low-confidence text needed a dedicated 7:1 token, and the matrix relies on tap-through for CI/n.
- Same freemium caveat as the others: the blur+Bayer scramble is a CSS filter over real values; production needs server-rendered decoys (now documented in-file).

---

## Appendix — Technique Library

All researched techniques, deduplicated across research angles, **sorted by wow × feasibility** (researcher's 1–5 estimates; feasibility is for a mobile-first 390px product, not a desktop art piece). Items appearing in multiple angles were merged to their strongest entry.

| W×F | Technique | Wow | Feas | Key sources |
|---|---|---|---|---|
| 25 | DSEG 7/14-segment LED font for hero numbers | 5 | 5 | https://www.keshikan.net/fonts-e.html · https://github.com/keshikan/DSEG |
| 25 | Game Boy DMG 4-tone palette as luminance-ordered semantic ramp (CVD-safe by construction) | 5 | 5 | https://lospec.com/palette-list/dmg-01-accurate · https://www.datylon.com/blog/data-visualization-for-colorblind-readers |
| 20 | Retro-OS instrument register: boot-screen metaphor + constraint-driven mono grid | 5 | 4 | https://poolsuite.net/ · https://teenage.engineering/designs |
| 20 | Berkeley Mono / U.S. Graphics industrial-datasheet brand language | 5 | 4 | https://usgraphics.com/products/berkeley-mono · https://news.ycombinator.com/item?id=38322793 |
| 20 | Handjet variable pixel font for animated de-rez/resolve (wght/ELSH/ELGR axes) | 5 | 4 | https://github.com/rosettatype/handjet · https://fonts.google.com/specimen/Handjet |
| 20 | Low-tech Magazine pattern: build-time dithered images + CSS blend-mode tinting (~1–2KB/asset) | 4 | 5 | https://solar.lowtechmagazine.com/about/the-solar-website/ |
| 20 | Pure CSS halftone: radial-gradient dots + gradient map + filter:contrast() | 4 | 5 | https://frontendmasters.com/blog/pure-css-halftone-effect-in-3-declarations/ · https://css-irl.info/css-halftone-patterns/ |
| 20 | Dither-degradation as the freemium teaser language (downscale + image-rendering:pixelated) | 4 | 5 | https://developer.mozilla.org/en-US/docs/Web/CSS/image-rendering · https://css-tricks.com/keep-pixelated-images-pixelated-as-they-scale/ |
| 20 | Departure Mono as identity font (pixel mono built for tabular data, SIL OFL) | 4 | 5 | https://departuremono.com/ · https://github.com/rektdeckard/departure-mono |
| 20 | Ultimate Oldschool PC Font Pack (IBM VGA/EGA webfonts) for dense table bodies | 4 | 5 | https://int10h.org/oldschool-pc-fonts/ |
| 20 | Pixel-borders / NES.css stepped-corner chrome (SVG border-image) | 4 | 5 | https://nigelotoole.github.io/pixel-borders/ · https://nostalgic-css.github.io/NES.css/ |
| 20 | Character-grid layout ('The Monospace Web' pattern) | 4 | 5 | https://owickstrom.github.io/the-monospace-web/ |
| 20 | Pure-CSS CRT layer: scanlines + power-on boot (once, reduced-motion-gated) | 4 | 5 | https://aleclownes.com/2017/02/01/crt-display.html · https://dev.to/ekeijl/retro-crt-terminal-screen-in-css-js-4afh |
| 20 | Bloomberg amber-on-black density doctrine | 4 | 5 | https://news.ycombinator.com/item?id=19153875 |
| 20 | Unicode block-character sparklines (▁▂▃▄▅▆▇█) | 4 | 5 | https://rosettacode.org/wiki/Sparkline_in_unicode · https://blog.jonudell.net/2021/08/05/the-tao-of-unicode-sparklines/ |
| 20 | Terminal-brand web chrome: bracketed nav, line-number gutter, ASCII boot/loading | 4 | 5 | https://www.terminal.shop/ · https://charm.land/blog/terminaldotshop/ |
| 20 | Clip-path glitch with steps() timing + RGB split (event-driven only) | 4 | 5 | https://alvarotrigo.com/fullPage/css-glitch-effect/ |
| 20 | Monospace-brutalist section indexing + oversized wordmark blocks | 4 | 5 | https://basement.studio/ |
| 20 | Google Fonts pixel accent bench (Silkscreen, Press Start 2P, VT323, Handjet…) | 4 | 5 | https://fonts.google.com/specimen/Silkscreen · https://fonts.google.com/specimen/Press+Start+2P |
| 20 | Dual-phosphor semantic system (P1 green = signal, P3 amber = caution/low-confidence) | 4 | 5 | https://en.wikipedia.org/wiki/Monochrome_monitor |
| 20 | Risograph 2-color overprint identity (pink #FF48B0 + teal #00838A + multiply overlap) | 4 | 5 | https://github.com/mattdesl/riso-colors · https://stencil.wiki/wiki/Category:Riso_inks |
| 16 | Ordered Bayer dither as brand texture (tiled PNG everywhere, shader for one hero only) | 4 | 4 | https://blog.maximeheckel.com/posts/the-art-of-dithering-and-retro-shading-web/ · https://www.magicpattern.design/tools/dither-generator |
| 16 | Pure-CSS halftone hover/tap reveals (locked = halftone, premium = full art) | 4 | 4 | https://leanrada.com/notes/pure-css-halftone/ · https://speckyboy.com/combining-halftone-effects-with-code/ |
| 16 | F1 live-timing-tower layout for ranked meta list | 4 | 4 | https://f1-dash.com/ · https://github.com/pesaventofilippo/f1dash |
| 16 | System-7/Y2K window chrome with dither fills + in-fiction dates | 4 | 4 | https://poolsuite.net/ |
| 15 | Full-viewport interactive Bayer-dither WebGL background (<0.2ms/frame claim) | 5 | 3 | https://tympanus.net/codrops/2025/07/30/interactive-webgl-backgrounds-a-quick-guide-to-bayer-dithering/ |
| 15 | Real-time image dithering + pixelation post-processing shader | 5 | 3 | https://tympanus.net/codrops/2025/06/04/building-a-real-time-dithering-shader/ · https://github.com/niccolofanton/dithering-shader |
| 15 | Cluster-dot halftone + duotone gradient mapping for charts (open data-viz lane) | 5 | 3 | https://maximmcnair.com/p/webgl-dithering |
| 15 | Live SVG pixelation filter on rendered HTML (no Safari support — needs fallback) | 5 | 3 | https://meyerweb.com/eric/thoughts/2023/12/21/pixelating-live-with-svg/ · https://www.fancycomponents.dev/docs/components/filter/pixelate-svg-filter |
| 15 | Bayer-dither dissolve transition (shader, CSS-mask fallback) | 5 | 3 | https://blog.maximeheckel.com/posts/the-art-of-dithering-and-retro-shading-web/ · https://www.shadertoy.com/view/7sfXDn |
| 15 | Bayer-dither obscuring instead of gaussian blur for premium gating | 5 | 3 | https://blog.maximeheckel.com/posts/the-art-of-dithering-and-retro-shading-web/ · https://shaders.paper.design/dithering |
| 15 | Atkinson / error-diffusion dithering at build time (ditherpunk canon) | 3 | 5 | https://surma.dev/things/ditherpunk/ · https://www.npmjs.com/package/canvas-dither |
| 15 | Grainy gradients: feTurbulence + contrast squash (also fixes dark-mode banding) | 3 | 5 | https://css-tricks.com/grainy-gradients/ |
| 15 | Trend validation: dithering as active 2025–26 award-circuit aesthetic | 3 | 5 | https://onepagelove.com/tag/dither-effect · https://efecto.app/ |
| 15 | image-rendering:pixelated + font-smoothing:none crispness foundation | 3 | 5 | https://developer.mozilla.org/en-US/docs/Games/Techniques/Crisp_pixel_art_look |
| 15 | WebTUI attribute-driven TUI CSS kit (mockup accelerator; vendor it, 0.x) | 3 | 5 | https://github.com/webtui/webtui |
| 15 | Mobile-dense-table doctrine (sticky first col/header, tabular numerals, bottom sheets) | 3 | 5 | https://www.pencilandpaper.io/articles/ux-pattern-analysis-enterprise-data-tables |
| 15 | Phosphor glow done cheap (pre-paint shadow, animate opacity only) | 3 | 5 | https://www.sitepoint.com/css-box-shadow-animation-performance/ |
| 15 | Infinite marquee/ticker for live data (CSS duplicate-track; Motion+ for production) | 3 | 5 | https://motion.dev/magazine/building-the-ultimate-ticker · https://www.smashingmagazine.com/2024/04/infinite-scrolling-logos-html-css/ |
| 15 | Number roll-ups: CountUp.js quantized with stepped easing | 3 | 5 | https://github.com/inorganik/countUp.js/ |
| 15 | Pixel cursor (desktop) + chunky :active press states (mobile) | 3 | 5 | https://developer.mozilla.org/en-US/docs/Web/CSS/cursor |
| 15 | Pixel/stepped SVG sparklines with shape-rendering:crispEdges | 3 | 5 | https://alexplescan.com/posts/2023/07/08/easy-svg-sparklines/ |
| 15 | GitHub-contribution-graph quantized color steps for small grid cells | 3 | 5 | https://github.com/kevinsqi/react-calendar-heatmap |
| 15 | IBM Plex Mono / Commit Mono / JetBrains Mono as free data-table workhorses | 3 | 5 | https://fonts.google.com/specimen/IBM%2BPlex%2BMono · https://commitmono.com/ |
| 15 | Warm-retro 'calm hardware' light palette (Daylight Computer counterweight) | 3 | 5 | https://daylightcomputer.com/ |
| 15 | Monospace-brutalism as explicit market positioning (2026 trend confirmation) | 3 | 5 | https://dev.to/studiomeyer_io/web-design-trends-2026-what-actually-held-up-after-six-months-23p8 · https://www.diabrowser.com/ |
| 15 | Pure-CSS Y2K chrome (PRO badge) + blue-orange CVD-safe diverging scale | 3 | 5 | https://ibelick.com/blog/creating-metallic-effect-with-css · https://colorbrewer2.org/ |
| 12 | Card-game matchup-matrix precedents: vS Data Reaper, MetaMage (interaction model to beat) | 3 | 4 | https://www.vicioussyndicate.com/drr/matchup-chart-data-reaper-report/ · https://www.metamages.com/sessions/8532707e-04a5-40da-9eca-e96b67f2e21d |
| 12 | Prediction-market probability display patterns (rolling numbers, desaturated deltas) | 3 | 4 | https://avark.agency/learn/prediction-market-design-patterns |
| 10 | Indexed-palette dither post-process shader at product scale (basement Chronicles, Awwwards SOTD) | 5 | 2 | https://www.awwwards.com/the-making-of-bsmnt-chronicles.html |
| 10 | No-motion-first / reduced-motion architecture (FULL/SUBTLE/OFF toggle) | 2 | 5 | https://web.dev/articles/prefers-reduced-motion · https://www.tatianamac.com/posts/prefers-reduced-motion |
| 10 | Accessibility guardrails for CRT effects (flash limits, contrast on solid core) | 2 | 5 | https://web.dev/learn/accessibility/motion · https://css-tricks.com/accessible-web-animation-the-wcag-on-animation-explained/ |
| 5 | COUNTEREXAMPLE — full-screen audiovisual dither shaders are desktop art pieces (Astro Dither) | 5 | 1 | https://recent.design/i/rlgsqpq-astro-dither · https://astrodither.robertborghesi.is/ |

Reading of the table: the top of the leaderboard is dominated by **zero-JS, build-time, or pure-CSS techniques** (DMG ramp, DSEG, build-time dither+tint, CSS halftone, character grid). Every WebGL item sits at feasibility ≤3. The identity can ship without a single shader; shaders are garnish for one bounded hero surface at most (the Astro Dither counterexample defines the boundary).

---

## Next steps

**1. Prototype Pit-Wall Console for real (recommended).**
Build S1 + S2 in the actual frontend stack against real M1 data (not mock arrays): timing tower, matrix with hatch-encoded low-n, DSEG drilldown, ticker fed by real ingest events. Success criteria: data legibility and mobile ≥8 on both screens in a re-critique, all touch targets ≥44px measured, reduced-motion path fully specced.

**2. Port the honesty furniture regardless of winner.**
Grinder Terminal produced product features disguised as aesthetics: ingest-tied freshness indicator (never a fake LIVE), CI-clear-of-50% coloring rule, provenance line (events · source split · window · n), low-n rendered visibly noisy/hatched. These fit the plan's statistical-rigor pitch and should ship in any direction.

**3. WebGL spikes needed (time-boxed, before committing to any wow-5 effect):**
- Bayer-dither background/dissolve on mid-tier Android (frame cost, battery, DPR cap) — the Codrops 0.2ms claim is desktop-only.
- Cluster-dot halftone matrix as one canvas/quad vs. the pure-CSS per-cell recipe already proven in the Overprint S2 mockup — the CSS version may make the WebGL one unnecessary.
- Live SVG pixelation filter: confirm the Safari no-support fallback path before anyone designs around it.

**4. Non-WebGL spike: build-time Atkinson pipeline.**
node + canvas-dither, linear-space luminance, PNG-8 output, blend-mode tint. Overprint's image system is currently all placeholders; this is a half-day spike that also serves the other directions' asset needs.

**5. Freemium gating is a backend requirement, not CSS.**
All nine mockups leak premium values in free-tier DOM in some form (documented as mock-only in each file). Production rule: free tier receives server-rendered decoys or omitted fields via the entitlements module; client filters are presentation only.

**6. Open questions for the owner:**
- **Card-art ToS:** does heavily-dithered/halftoned card art clear the WotC fan-content line? Blocks Overprint's image system and any card art anywhere. (Per project rules: ask, don't guess.)
- **Berkeley Mono license/pricing:** unverified this session (site blocks fetch); free stack (Departure + Plex/JetBrains Mono) covers V1 either way.
- **Is Overprint the light theme / report-export identity of the Pit-Wall app,** rather than a competing direction? The riso weekly-report export image is a strong Discord growth artifact regardless.
- **Motion budget:** is the Pit-Wall FULL/SUBTLE/OFF toggle acceptable scope for V1, or should V1 ship SUBTLE-only?
- **File housekeeping:** mockups are split across `grinder-terminal/`, `overprint-bulletin/`, and `mockups/…` — consolidate before sharing.

---

*All critique scores and issue lists in this report are quoted from the overnight critique/revision runs; nothing here was re-measured after the fact. Technique wow/feasibility scores are researcher estimates from the research pass, not benchmarks.*
