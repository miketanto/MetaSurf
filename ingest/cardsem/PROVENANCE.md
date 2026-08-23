# Provenance — `features.tsv.gz`

Mechanical card-feature vectors imported from the CardGuru project. Same
posture as `archetypes/definitions/`: pinned, committed data with a recorded
origin — **not** a code dependency. MetaSurf never imports CardGuru, never
needs a Forge or XMage checkout, and never reaches the network for this file.

## Pins

| what | value |
|---|---|
| Source project | CardGuru (`miketanto/CardGuru`) |
| Source file | `rl/e2_features.tsv` |
| Commit that produced the file | `0ddc7237eb61db20e11d6f0e149ab11084d1a8cd` |
| CardGuru HEAD at import time | `5cfafebfcabe5090d243cd983a0138d45dac69f5` |
| Extractor | `rl/e2_extract.py` |
| Upstream card-script source | Forge `670429bf` (cardsfolder) |
| Imported | 2026-08-23 |

## Checksums

    sha256(rl/e2_features.tsv)        1ea3d5aefc4fde01910210882c8f6c45b29747a8185d7b728c4aee6f0ac6c984
    sha256(features.tsv.gz)           7c6792acd1bc0d2d560ff7ce774a6e2ea6cf39cf642c2d456f4e9b7ea9794de3

The gzip round-trip was verified byte-identical to the source at import time:

    gzip -dc ingest/cardsem/features.tsv.gz | sha256sum   # == source sha256

Committed gzipped (464 KB from 5.4 MB) following the precedent set for the
Scryfall bulk snapshot in commit `caba6e4` — rebuilds must be reproducible
from the repo alone.

## Contents

- 35,390 registered card names, 68 dimensions each.
- 871 combined `A // B` multi-face names; a multi-face card's vector is the
  union across its faces and is registered under each face name *and* the
  combined name.
- 763 all-zero vectors (2.16% of rows).
- 92 names contain non-ascii characters.

Dimension names are mirrored in `dims.py` (derived from the extractor source,
not transcribed). `tests/test_cardsem.py` asserts the row count, dimension
count and zero-vector count of the shipped file, so replacing it without
updating this document fails the suite.

## Regenerating after a pin bump

In a CardGuru checkout with its dataset built:

```bash
python3 rl/e2_extract.py --out rl/e2_features.tsv
gzip -9 -c rl/e2_features.tsv > <metasurf>/ingest/cardsem/features.tsv.gz
```

Then update the pins, checksums and counts above, update `dims.py` if the
feature space changed, and re-run `python -m ingest.cardsem` to regenerate the
coverage report. A pin bump changes the meaning of every column and is
therefore a deliberate, reviewed act — never a drive-by refresh.

## Known limitation (measured, not assumed)

The extractor's keyword list covers 18 keywords. Archetype-defining mechanics
outside it — `infect`, `cycling`, `delve`, `cascade`, `storm`, `dredge`,
`evoke`, `affinity`, `convoke`, `madness` — have no dimension, so a card whose
only ability is one of them extracts to an all-zero vector, indistinguishable
from a genuinely vanilla creature. See §3 of the coverage report for the
evidence and `dims.UNREPRESENTED_MECHANICS` for the asserted list. Extending
`KEYWORDS` in `rl/e2_extract.py` upstream is the fix.

## Licensing note

CardGuru operates under the WotC Fan Content Policy (non-commercial) and treats
Forge as a data source only. These vectors are derived mechanical descriptors,
not card text or art, but the licensing posture of the two projects differs and
must be settled by the owner before anything derived from this file ships in a
paid MetaSurf surface.
