# MTGODecklistCache — observed schema (M0 inspection note)

Everything below was observed by executing inspection code in this repo against the
frozen clone at commit `034735d588c388f9390dc5c29ee7c923e988e631` (2025-06-10, the
shutdown commit). Nothing here is assumed from documentation or memory. Survey
methodology: full structural key-union scan over a seeded random sample of 300 files
per large source (all files for manatraders/topdeck), plus targeted full scans over
all 8,019 Modern files for anomalies. Representative raw files are saved unmodified
under `tests/fixtures/MTGODecklistCache/`.

## Corpus layout

```
Tournaments/<source>/<yyyy>/<mm>/<dd>/<slug>.json
```

File counts (full scan, all formats):

| source                 | files  | years        |
|------------------------|--------|--------------|
| mtgo.com               | 27,095 | 2015–2024    |
| mtgo.com_limited_data  | 4,643  | 2024–2025    |
| melee.gg               | 3,606  | 2020–2025    |
| manatraders.com        | 49     | 2020–2024    |
| topdeck.gg             | 80     | 2024–2025    |
| **total**              | 35,473 |              |

`Tournaments-Archive/` also exists (wizards.com, starcitygames.com, channelfireball.com,
an old-data-model mtgo.com dump, and others). It is **not** imported in M0; noted as
optional backfill (plan ranks aggregator backfill lowest priority).

Per the repo README (and confirmed by the folder split): mtgo.com data from
**2024-06-20 onward** lives in `mtgo.com_limited_data` and is more limited (site change).

## CacheItem shape (identical across all five sources)

Top-level keys are exactly `Tournament`, `Decks`, `Rounds`, `Standings` in every
sampled file (no extras anywhere; 1,229 files sampled structurally).

```jsonc
{
  "Tournament": { "Date": "2020-03-21T00:00:00Z", "Name": "Modern Challenge", "Uri": "…" },
  "Decks": [
    {
      "Date": "2020-03-21T15:00:00",      // nullable (null on melee.gg/manatraders.com)
      "Player": "albert62",
      "Result": "1st Place",               // see result patterns below; can be ""
      "AnchorUri": "…",                    // mtgo anchor / melee decklist / moxfield link (topdeck)
      "Mainboard": [ { "Count": 4, "CardName": "Bloodbraid Elf" }, … ],
      "Sideboard": [ …same shape… ]
    }
  ],
  "Rounds": [                              // null on most mtgo files (leagues, prelims, dailies)
    { "RoundName": "Quarterfinals",        // "Round 1"…; topdeck uses bare "1", "2", …
      "Matches": [ { "Player1": "…", "Player2": "…", "Result": "2-0-0" } ] }
  ],
  "Standings": [                           // null on many mtgo files (all leagues)
    { "Rank": 1, "Player": "…", "Points": 24, "Wins": 10, "Losses": 2, "Draws": 0,
      "OMWP": 0.6793, "GWP": 0.7727, "OGWP": 0.61 }
  ]
}
```

Card entries are always `{CardName, Count}` — names only, **no card IDs of any kind**.
All card identity resolution is ours (Scryfall oracle_id via the `cards` table).
Split/aftermath/adventure cards appear as combined names with ` // ` (70 distinct in
Modern, e.g. `Alive // Well`, `Boom // Bust`); double-faced cards appear as
front-face-only names (e.g. `Fable of the Mirror-Breaker`).

## There is no Format field

Neither `Tournament` nor any other object carries the format. Format is recoverable
only from the filename/URI slug (`modern-league-…`, `…-modern-seat-4-…`). Full scan:
**143 of 35,473 files (0.4%) have no recognizable format token** (MOCS Opens/Playoffs,
Showcase Opens, championship/super qualifiers, e.g.
`mtgo.com/2019/03/09/2019-mocs-open-2019-03-0911818115.json`). These are skipped and
counted in the data-quality report — we do not guess formats from event-schedule
memory.

Melee event names are arbitrary (`Grand Open Qualifier Prague 2024`); the format token
is in the *filename*, added by the cache's own scraper. Team events are split by the
cache into per-seat files (`invasion-masters-modern-seat-4-72706-…`), so one melee
event id can span several files/formats — the filename stem, not the source's event
id, is the unique event key.

## mtgo event-type slugs (observed vocabulary, Modern)

`league` 3414 · `preliminary` 1788 · `challenge` 532 · `daily-swiss` 445 ·
`challenge-64` 361 · `challenge-32` 343 · `ptq-preliminary` 135 · `last-chance` 65 ·
`super-qualifier` 52 · `showcase-challenge` 49 · `ptq-finals` 31 · `challenge-96` 28 ·
`gold-league` 20 · `showcase-qualifier` 15 · `qualifier` 13 ·
`20th-anniversary-play-in` 12 · `mcq-finals` 11 · plus a long tail (`format-playoff`,
`players-tour-qualifier`, `challenge-*-special`, `mayhem`, `madness-finals`, …).

## Anomalies and edge cases observed (all kept as fixtures)

1. **Duplicate events.** 15 Modern filename stems appear under 2–3 different date
   directories (league re-publications around, but not only, the 2024-06 cutover; also
   within `mtgo.com_limited_data`). Verified: duplicate files contain **identical deck
   sets** (players + lists) with different bytes. Dedup key = filename stem,
   deterministic first-wins on sorted paths.
   Fixture pair: `mtgo.com/2024/02/03/` + `2024/02/04/modern-league-2024-02-037787.json`.
2. **Empty `Result` strings.** 3,120 Modern decks have `Result: ""` (mtgo
   preliminaries, clustered around late 2019).
   Fixture: `modern-preliminary-2019-12-2312052872.json`.
3. **`Decks` vs `Standings` mismatch.** 2,885 of 8,019 Modern files have
   `len(Decks) != len(Standings)` (when standings exist). Standings-only players are
   common (unpublished decklists: mtgo challenges pre-2024 publish fewer decks than
   standings rows; topdeck events include players with no list, e.g. fixture
   `the-ocho…` has 19 decks / 21 standings). Deck-only players also occur.
4. **Zero-card and tiny mainboards.** 48 Modern decks have an empty Mainboard, 104
   have <10 mainboard cards (melee no-submit artifacts).
   Fixture: `modern-20k-trial-scg-con-charlotte-friday-100-pm-silver-14033…` (melee).
   Related: melee.gg files can carry literal `{"Count": 0, ...}` card entries
   (3 entries across all Modern decks, 2 files, both melee.gg 2022; e.g. player
   `Hudson Tinch` in fixture `modern-30k-scg-con-dallas-…-2022-10-08.json` has
   Count 0 lines for two cards). Zero-count entries are dropped at
   normalization (a card with count 0 is not in the deck), counted in the DQ
   stats, and `count < 1` deck_cards rows fail the post-import gate.
5. **80+ card mainboards are real** (9,606 decks in the 80–89 bucket, Yorion-era),
   and a small number ≥100. Deck-size checks must be distribution reports, not hard
   ceilings.
6. **`Rounds` present ≠ full pairings.** mtgo challenges carry Top-8 bracket rounds
   only (`Quarterfinals`, …); melee/manatraders carry full swiss rounds
   (`Round 1`…`Round 18`); topdeck uses bare numeric round names. League/daily files
   have `Rounds: null`.
7. **Standings availability varies within mtgo**: in the 300-file mtgo sample,
   169 files had null Standings, 261 null Rounds; melee/manatraders/topdeck samples
   always had both.
8. **Points can be 0 while Wins > 0** (topdeck standings; e.g. rank-1 player with
   6 wins, Points 0) — Points is not a reliable cross-source signal.
9. **Result values** normalize to: `N-N` (league/swiss records like `5-0`),
   `N-N-N` in round Match results, `Nst/Nnd/Nrd/Nth Place`, or empty string.
10. **`&&` split-card separator in `mtgo.com_limited_data`.** Files from
   2024-10 onward write some split-card names as `A && B` (18 distinct names,
   4,752 occurrences corpus-wide, 4 in Modern; e.g.
   `Unholy Annex && Ritual Chamber` in
   `mtgo.com_limited_data/2024/11/…`). Each of the 18 matches a split card
   whose Scryfall name is `A // B` (verified against the 2026-07-07 bulk
   file, all `layout: split`). The resolver applies the mechanical
   `' && '`→`' // '` mapping as a last-resort lookup; unknown names still
   resolve to nothing.

## Rounds/Matches deep-dive (M2 inspection, executed 2026-07-07)

Full scan over all 8,019 Modern-token files in the frozen clone (same commit as
above), inspecting every `Rounds` entry. New fixture saved:
`melee.gg/2024/03/02/the-gathering-showdown-series-modern-52606-2024-03-02.json`
(duplicate `Player` among decks). All numbers below are printed output of the
scan scripts run in this session.

- **Presence.** Non-empty `Rounds` in 2,135 files: mtgo.com 926,
  mtgo.com_limited_data 543, melee.gg 635, manatraders.com 15, topdeck.gg 16.
  Rounds-bearing mtgo files are all challenge-family/qualifier events
  (`challenge` 531, `challenge-64` 361, `challenge-32` 343, `super-qualifier` 52,
  `showcase-challenge` 49, `ptq-finals` 31, …); **no league/preliminary/daily
  file carries Rounds** (confirms anomaly 6/7).
- **Shape.** All 9,466 round objects are exactly `{RoundName, Matches}`; all
  218,049 match objects are exactly `{Player1, Player2, Result}`. Every
  `Result` matches `N-N-N`.
- **Round names.** mtgo: `Quarterfinals`/`Semifinals`/`Finals` only (Top-8
  bracket; one anomaly, `modern-challenge-64-2024-02-1112611481.json`, has
  `[Quarterfinals, Quarterfinals, Semifinals]`). melee: `Round 1`…`Round 17`
  plus `Quarterfinals`/`Semifinals`/`Finals`/`Top 16`. manatraders:
  `Round 1`…`Round 10` + bracket names. topdeck: bare numerals `1`…`6` plus
  `Top 8`/`Top 4`/`Top 2`/`Top Power`/`Top Random`.
- **Result orientation is Player1's perspective** (`wins-losses-draws`).
  Verified via bracket advancement: in 10,175 bracket matches with a next
  round, the side with more wins in the result is the one appearing in the
  next round (0 opposite cases, 10 ambiguous on melee). Swiss cross-check:
  per-player match-win counts derived this way equal `Standings.Wins` exactly
  for 3,039/3,043 manatraders, 62,583/66,840 melee, and 352/432 topdeck player
  rows (melee diffs are dominated by events publishing zeroed standings, e.g.
  `lotus-box-patreon-championship-modern-1k-216-2020-04-05.json`).
- **Game counts vs match-level.** mtgo/melee/manatraders results are game
  counts (`2-0-0`, `2-1-0`, `0-2-0`, …; melee also `0-0-3` ×2,549 —
  intentional draws — `1-1-0` ×3,413, `0-0-0` ×193, `1-1-1` ×441).
  topdeck.gg uses **match-level** results only: `1-0-0` ×1,038, `0-0-1` ×129.
  Comparing wins vs losses gives the match outcome uniformly in both
  encodings; `wins == losses` ⇒ draw.
- **Byes.** `Player2` is `null` on manatraders (×52, result `2-0-0`) and `""`
  on topdeck (×34, result `0-0-1`). No other source has missing players.
- **Player→deck resolution.** Match-player slots without a same-`Player` deck
  row: melee.gg 19,081 (of 2×197,426 slots; 14,475 of them appear in
  Standings), manatraders 940, topdeck 427, mtgo.com/_limited_data **0**.
  Exactly 2 rounds-bearing events have a duplicate `Player` among decks
  (`the-gathering-showdown-series-modern-52606-2024-03-02.json`:
  `Cesar Hernandez` ×2; `special-10-entry-10k-rcq-…-14036-2023-03-05.json`:
  `removed removed` ×2) — resolution there is ambiguous, never guessed.
- **Duplicate match rows.** 2 corpus-wide, both melee, both a drawn match
  recorded once per orientation (`0-0-1` A-vs-B and B-vs-A in the same round).
  No `Player1 == Player2` self-matches anywhere.

## M0 normalization decisions driven by the above

- Event key: `(source, filename-stem)`; duplicates skipped deterministically + counted.
- Format: filename-token match against `formats` config; unmatched files skipped + counted.
- Decks are the primary entity; standings enrich matching decks with
  wins/losses/draws/rank (match on exact `Player` string); standings-only rows are
  counted in the DQ report (no deck row is fabricated).
- `Result` parsed for `finish_rank` (`Nth Place`) or W-L (`N-N`) when standings are
  absent; empty string → nulls.
- `Rounds` are **not** parsed into `matches` in M0 (match extraction is M2 per plan);
  raw files remain the source of truth (`events.raw_ref` points at the cache path).
- All cards resolve through the `cards` table; unresolved names go to the
  unresolved-cards report, never guessed.
