# MTGOFormatData / MTGOArchetypeParser — observed structure (M1 inspection note)

Observed by executing inspection code against real clones; nothing assumed from
memory. Sources (both cloned via git, which the environment's network policy
allows):

- `github.com/Badaro/MTGOFormatData` @ `71af318018d51ea590b16775433ae92ce34a8000`
  (2026-06-30 — the repo is still receiving commits, contrary to the plan §3
  "unmaintained" note; treat our port as a pinned snapshot).
- `github.com/Badaro/MTGOArchetypeParser` @ `50eeb29becf3b44d2d99ed8be4c8581501efd5aa`
  (reference implementation; semantics below quote its `ArchetypeAnalyzer.cs`).

Representative rule files are saved unmodified under
`tests/fixtures/MTGOFormatData/`; the full Modern set is ported unmodified to
`archetypes/definitions/` (see `PROVENANCE.md` there, incl. the licensing note:
MTGOFormatData has no LICENSE file; the parser repo is MIT).

## Layout

```
Formats/card_colors.json            # global color tables: {Lands: [{Name, Color}], NonLands: [...]}
Formats/<Format>/Archetypes/*.json  # Modern: 130 files
Formats/<Format>/Fallbacks/*.json   # Modern: 9 files
Formats/<Format>/metas.json         # meta periods: [{StartDate, Name}], Modern: 2015-11-01 .. present
Formats/<Format>/color_overrides.json
```

All 139 Modern rule files parse as strict JSON (no BOM in any rule file; the
C# sources carry BOMs). `Modern/color_overrides.json` is **relaxed JSON**: a
trailing comma before `]` and `"NonLands": null` — the reference's
Newtonsoft.Json accepts both, so our loader strips trailing commas on retry
and treats null sections as empty. `card_colors.json`: 8,527 Lands / 19,915
NonLands entries.

## Rule-file shape (Modern, full survey)

Archetype file: `{Name, IncludeColorInName, Conditions: [...], Variants?: [...]}`
(22 variants total; variants have the same shape, nested one level).
Fallback file: `{Name, IncludeColorInName, CommonCards: [...]}`.

Condition `{Type, Cards: [...]}` — observed Type vocabulary and counts:
`DoesNotContain` 224 · `InMainboard` 222 · `OneOrMoreInMainboard` 77 ·
`TwoOrMoreInMainboard` 25 · `DoesNotContainMainboard` 12 · `InSideboard` 2 ·
`InMainOrSideboard` 2 · `TwoOrMoreInMainOrSideboard` 1 ·
`OneOrMoreInMainOrSideboard` 1. (The reference enum also defines
`OneOrMoreInSideboard`, `TwoOrMoreInSideboard`, `DoesNotContainSideboard`,
unused in Modern.)

## Exact matching semantics (from `ArchetypeAnalyzer.cs`)

- Card matching is exact string equality on names; counts are irrelevant except
  where noted. Empty/missing `Cards` ⇒ the condition is skipped.
- `In*` and `DoesNotContain*` types use **only `Cards[0]`** even when more
  cards are listed. `OneOrMore*`: at least one listed name present in the zone.
  `TwoOrMore*`: at least **two distinct listed names** present (deck entries
  matched, not copies). `DoesNotContain` checks main AND side.
- An archetype matches iff **all** conditions hold. If a matched archetype has
  variants, each matching variant **replaces** the parent in the result
  (parent kept only when no variant matches).
- ≥2 specific archetypes matching = a conflict; the reference reports
  `Conflict(...)` by default or keeps the one with fewest conditions under
  `PreferSimpler`.
- Fallbacks run **only when no specific archetype matched**: score = sum of
  deck counts of cards whose name is in `CommonCards` (main+side, distinct
  entries); best score wins, ties broken by fewer `CommonCards`; the match
  counts only if score / (mainboard entries + sideboard entries) > 0.1
  (`minSimiliarity`, on distinct-entry counts, not card copies).
- Color identity: count W/U/B/R/G separately over land and non-land tables
  (`card_colors.json` + per-format overrides, all zones, weighted by copies);
  a color is in the deck's identity iff it appears in **both** a land and a
  non-land. `IncludeColorInName` prefixes the guild/shard name (or
  `Mono<Color>`) to the archetype name; `"Generic"` is stripped from fallback
  names; PascalCase is split into words.

## Cross-checks against our corpus/cards data (executed)

- 526 distinct card names are referenced by Modern conditions/CommonCards.
  **524 resolve** through our cards table; the 2 failures are upstream
  data typos, both mechanically mappable and both verified unambiguous under
  NFKD-diacritic/whitespace folding across all 34,213 playable cards:
  - `" Bottled Cloister"` (leading space, `Archetypes/WhirPrison.json`),
  - `"Troll of Khazad-dum"` (corpus + Scryfall both spell it
    `Troll of Khazad-dûm`; 15,890 corpus occurrences of the û form, 0 of the
    ascii form). These conditions are dead in the reference implementation
    too; our engine maps rule names to card ids via the resolver plus a
    fold-fallback that applies only when it hits exactly one card, and logs
    every fallback use. Flagged upstream-typo list to the owner.
- 59 of 28,442 color-table names don't resolve against our cards table:
  Arena-only `A-` rebalances absent from this bulk snapshot and doubled
  `X // X` names from Scryfall's reversible-card representation (a layout our
  oracle-cards snapshot does not contain). None can occur as corpus deck
  names; they are inert entries, not errors.
- 30 NFKD-fold keys are ambiguous across playable cards (face-name overlaps
  like `Monster`), which is why the fold-fallback is exact-one-hit-only.

## Port decisions (implemented in `archetypes/classifier/`)

1. Definitions are data, ported unmodified; the engine reimplements the
   reference semantics above (no .NET dependency, no code copied).
2. Rule card names resolve to `cards.id` at engine-load time; decks are
   classified as vectors of `cards.id` (our deck storage), making rule
   matching independent of name-form drift between sources.
3. Conflicts are resolved `PreferSimpler` (fewest conditions) for label
   generation, with the conflict set recorded per deck for audit.
4. Every label carries `classifier_version` = hash of (definitions snapshot,
   engine version string).
