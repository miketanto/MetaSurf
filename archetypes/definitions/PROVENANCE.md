# Provenance of ported archetype definitions

Ported unmodified from `github.com/Badaro/MTGOFormatData`, commit
`71af318018d51ea590b16775433ae92ce34a8000` (2026-06-30), per plan §3
("Seed for the rules layer of archetype classification. Port the definition
format; do not depend on the .NET runtime.").

- `modern/Archetypes/` (130 files), `modern/Fallbacks/` (9 files),
  `modern/metas.json`, `modern/color_overrides.json`
  ← `Formats/Modern/` in the source repo.
- `standard/Archetypes/` (59 files), `standard/Fallbacks/` (8 files),
  `standard/metas.json`, `standard/color_overrides.json`
  ← `Formats/Standard/` (the *active* Standard set; the source repo also keeps
  dated historical folders `Standard-YYYYMMDD-YYYYMMDD/` for past rotations).
  Ported unmodified at the same pinned commit. **Observed upstream typo:**
  `standard/Archetypes/UWMomo.json` has a condition type `"OneorMoreInMainboard"`
  (lowercase `or`). The data is kept byte-identical; the loader canonicalizes
  condition-type casing (`archetypes/classifier/definitions.py`) so pure case
  typos resolve while genuinely-unknown types still fail.
- `card_colors.json` ← `Formats/card_colors.json` (global land/non-land color
  table used for color detection and IncludeColorInName).

Matching semantics were reimplemented in `archetypes/classifier/` from reading
the companion `MTGOArchetypeParser` source (MIT-licensed, © Filipe Badaró),
commit `50eeb29becf3b44d2d99ed8be4c8581501efd5aa` — no code was copied. See
`docs/notes/mtgoformatdata-observed-schema.md` for the observed rule-file
structure and the exact condition semantics.

**Licensing note (flagged to owner):** MTGOFormatData itself carries no
LICENSE file (checked at the pinned commit; the parser repo is MIT). The
plan directs porting these definitions; if the project ever redistributes
them commercially, resolve licensing with the maintainers first.

Do not hand-edit definition files here; changes to archetype definitions are
data changes that must reference observed decklists, and any gap found is
flagged to the owner rather than authored from memory (CLAUDE.md rule 4).
