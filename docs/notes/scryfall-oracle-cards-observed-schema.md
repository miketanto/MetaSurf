# Scryfall oracle-cards bulk file — observed schema (M0 inspection note)

Everything below was observed by executing inspection code in this repo against the
bulk file described under Provenance. Nothing is assumed from documentation or
memory. Representative raw card objects (byte-exact lines) are saved under
`tests/fixtures/scryfall/oracle-cards-sample.jsonl`.

## Provenance

The environment's network policy blocks `api.scryfall.com` and `data.scryfall.io`
directly (proxy CONNECT 403, verified 2026-07-07), so the official bulk file was
downloaded by the owner from Scryfall and relayed into the session:

- Original file: `oraclecards20260707090318.jsonl.gz` (per Scryfall's timestamped
  naming, generated 2026-07-07); relayed as an upload, 22,735,562 bytes,
  SHA-256 `f24b6cf4555f1ca4e8d5066af2df52723e7e39f65289b02ab39be36cbd4b726e`.
- Decompressed to `data/scryfall/oracle-cards.jsonl`, 179,283,541 bytes,
  SHA-256 `c01460e3e9d76b6d4e44a99e1cd8c2b3721d97c82203843cfef2c7e556672240`.
- Format is **JSONL** (one card object per line, no enclosing array) — Scryfall's
  new bulk format. Per Scryfall's blog (July 2026, read via web search — not
  independently verified from this container), the old JSON-array framing is
  served in parallel only until 2026-07-20, so the importer treats JSONL as the
  primary framing and sniffs the array framing for compatibility.

## Shape

38,233 lines; every line parses as JSON; every object has `"object": "card"`.
**Every object has a top-level `oracle_id`; all 38,233 are distinct** (0 missing,
0 duplicates). 48 keys are present on all objects (incl. `id`, `oracle_id`,
`name`, `layout`, `type_line`, `set`, `set_type`, `legalities`, `games`,
`digital`); notable optional keys: `card_faces` (3,194), `mana_cost`/`colors`/
`image_uris` (35,409 — absent exactly on multifaced cards), `oracle_text`
(35,039), `all_parts` (6,796).

## Layouts (full distribution)

`normal` 32,985 · `art_series` 2,243 · `token` 1,194 · `transform` 401 ·
`planar` 207 · `saga` 168 · `adventure` 157 · `split` 137 · `vanguard` 107 ·
`scheme` 102 · `modal_dfc` 100 · `emblem` 87 · `double_faced_token` 80 ·
`prepare` 50 · `class` 38 · `mutate` 34 · `flip` 26 · `leveler` 26 · `meld` 21 ·
`prototype` 21 · `host` 20 · `case` 15 · `augment` 14

`card_faces` is present on exactly 8 layouts — `art_series`, `double_faced_token`,
`prepare`, `transform`, `modal_dfc`, `split`, `adventure`, `flip` — and in each of
those layouts **every** card's top-level `name` is the combined `"Front // Back"`
form (counts match exactly). Faces are `{name, ...}` objects; face-level
`oracle_id` never occurs in this file (no reversible_card layout present).
`meld` cards have no `card_faces`; each meld part is its own object.

## How this meets the decklist corpus (see mtgodecklistcache-observed-schema.md)

- Corpus split/aftermath/adventure names like `Alive // Well` match the top-level
  `name` of `split`/`adventure` cards verbatim (spot-checked `Alive // Well`,
  `Boom // Bust` — both present, layout `split`, faces `['Alive','Well']` /
  `['Boom','Bust']`).
- Corpus DFC references are front-face-only (`Fable of the Mirror-Breaker`); the
  bulk object's name is `Fable of the Mirror-Breaker // Reflection of Kiki-Jiki`
  (layout `transform`), so the **resolver must index face names** as well as full
  names. 30 `modal_dfc` cards have their front-face name occurring in the saved
  corpus fixtures (e.g. `Clearwater Pathway`), corroborating the convention.

## Name collisions observed (drive the import/resolution rules)

- **2,320 names** are shared between playable-layout cards and non-playable-layout
  objects (`token`/`double_faced_token`/`emblem`/`art_series`/`vanguard`/`scheme`/
  `planar`) — e.g. `Adorned Pouncer` exists as an expansion card and as a token.
  → Non-playable layouts are **excluded from import** (4,020 objects); keeping
  them would let decklist names resolve to tokens.
- Among the remaining 34,213 playable cards, **14 full names appear on >1 object**.
  All are un-set/playtest/memorabilia variants colliding with themselves or with a
  real card. Three collide with real tournament cards: `Fast // Furious`
  (funny `unk` vs MH2), `Pick Your Poison` and `Red Herring` (playtest `cmb2` vs
  MKM); plus `Unquenchable Fury` (commander `nec` vs memorabilia `tbth`).
  In every such case the two sides are separated by
  `set_type ∈ {funny, memorabilia}` vs not.
  → The importer assigns `attrs.resolution_tier` = 1 for `set_type` in
  {`funny`, `memorabilia`}, else 0, and inserts cards ordered by
  `(resolution_tier, oracle_id)`; the resolver's first-wins-by-id rule then
  deterministically prefers the real card.
- **25 playable face names equal some other playable card's full name** (e.g.
  face `Brainstorm` of `Harmonized Trio // Brainstorm`, layout `prepare`).
  The resolver's existing "full names win over face names" rule handles this;
  the collision list confirms the rule is load-bearing, not theoretical.
- 5 face names are shared by two playable cards (e.g. `Fire` in `Fire // Ice`
  and `Start // Fire`); first-wins by `(resolution_tier, oracle_id)` order makes
  the choice deterministic. Corpus decklists reference such cards by their
  combined name, so the face entry is a fallback only.

## Other observations

- `set_type` distribution includes `alchemy` (746) and `games == ['arena']`-only
  cards (989; 217 names start with `A-`). Their names do not collide with any
  paper card's full name (checked across all 34,213 playable cards), so they are
  imported like any other card rather than special-cased.
- `digital: true` on 2,141 objects; `games` values observed:
  paper 36,092 · mtgo 28,769 · arena 12,095 · astral 10 · sega 8.
- `legalities` carries 23 format keys (incl. `modern`); not imported into attrs
  in M0 (legality is temporal — a snapshot would be misleading for backtests).

## Import decisions (implemented in `ingest/scryfall/`)

1. Parse JSONL (sniff `[` for the legacy array framing).
2. Skip layouts {token, double_faced_token, emblem, art_series, vanguard,
   scheme, planar}; count skips per layout and print them.
3. `canonical_ref` = `oracle_id`; `name` = top-level combined name.
4. `attrs` = `{layout, set_type, type_line, resolution_tier}` +
   `face_names` (list, only when `card_faces` present).
5. Insert ordered by `(resolution_tier, oracle_id)` so `cards.id` order encodes
   resolution preference deterministically.
