"""Parse CardGuru's feature TSV and join it to canonical card identities.

Observed format of the real file (35,390 rows, verified this session):

    68                                  <- line 1: dimensionality, nothing else
    <card name>\t<v1,v2,...,v68>        <- one row per registered name
    ...

Observed properties that drive the parser (all counted on the real table, not
assumed):

- Rows are sorted by name; 871 are combined "A // B" multi-face names, whose
  vector is the UNION across faces and is *also* registered under each face
  name separately.
- 763 rows are all-zero — the extractor found no scripted mechanics on that
  card. This is materially different from "card absent from the table", so the
  two are reported separately and never collapsed (see `zero_vector_names`).
- 92 names contain non-ascii characters, which is why the fallback match tier
  folds accents rather than requiring byte equality.

Failure posture: a malformed row raises. A short vector, a non-numeric value,
a missing tab, or a duplicate name means the pin is wrong or the file is
truncated — that is a broken input, not a partial dataset, and silently
dropping rows would quietly degrade every downstream vector (CLAUDE.md:
"fail loudly instead of ingesting garbage").
"""

from __future__ import annotations

import gzip
import unicodedata
from collections.abc import Hashable, Iterable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Generic, TypeVar

K = TypeVar("K", bound=Hashable)

Vector = tuple[float, ...]


class FeatureTableError(ValueError):
    """The feature table is malformed. Never raised for a merely absent card."""


def fold_name(name: str) -> str:
    """Accent- and case-folded form used only as a *fallback* match tier.

    Mirrors CardGuru's own normalizer (research/scripts/join_scryfall.py):
    NFKD-decompose, drop non-ascii, casefold, strip. This is deliberately not
    fuzzy — it collapses encoding and case differences and nothing else. Card
    identity is data, never a guess (CLAUDE.md rule 3).
    """
    decomposed = unicodedata.normalize("NFKD", name)
    ascii_only = decomposed.encode("ascii", "ignore").decode("ascii")
    return ascii_only.casefold().strip()


@dataclass(frozen=True)
class FeatureTable:
    """Parsed feature table. `vectors` is keyed by the name as written."""

    dim: int
    vectors: dict[str, Vector]
    zero_vector_names: frozenset[str]
    _folded: dict[str, str] = field(default_factory=dict, repr=False)

    def lookup(self, name: str) -> tuple[Vector | None, str | None]:
        """Return (vector, tier) where tier is 'exact' | 'folded' | None."""
        hit = self.vectors.get(name)
        if hit is not None:
            return hit, "exact"
        folded = self._folded.get(fold_name(name))
        if folded is not None:
            return self.vectors[folded], "folded"
        return None, None


def parse_feature_table(lines: Iterable[str]) -> FeatureTable:
    """Parse TSV lines into a FeatureTable. Raises FeatureTableError on any
    malformed row — see the module docstring for why this is strict."""
    it = iter(lines)
    try:
        header = next(it).strip()
    except StopIteration:
        raise FeatureTableError("feature table is empty") from None
    try:
        dim = int(header)
    except ValueError:
        raise FeatureTableError(
            f"first line must be the dimensionality, got {header!r}"
        ) from None
    if dim <= 0:
        raise FeatureTableError(f"dimensionality must be positive, got {dim}")

    vectors: dict[str, Vector] = {}
    zeros: set[str] = set()
    for lineno, raw in enumerate(it, start=2):
        line = raw.rstrip("\n")
        if not line.strip():
            continue
        if "\t" not in line:
            raise FeatureTableError(f"line {lineno}: no tab separator: {line[:60]!r}")
        name, _, payload = line.partition("\t")
        if not name:
            raise FeatureTableError(f"line {lineno}: empty card name")
        if name in vectors:
            raise FeatureTableError(f"line {lineno}: duplicate card name {name!r}")
        parts = payload.split(",")
        if len(parts) != dim:
            raise FeatureTableError(
                f"line {lineno}: {name!r} has {len(parts)} values, expected {dim}"
            )
        try:
            vector = tuple(float(p) for p in parts)
        except ValueError:
            raise FeatureTableError(
                f"line {lineno}: {name!r} has a non-numeric feature value"
            ) from None
        vectors[name] = vector
        if not any(vector):
            zeros.add(name)

    # Folded index for the fallback tier. First name wins on collision, and
    # names are consumed in the file's sorted order, so this is deterministic.
    folded: dict[str, str] = {}
    for name in vectors:
        folded.setdefault(fold_name(name), name)

    return FeatureTable(
        dim=dim, vectors=vectors, zero_vector_names=frozenset(zeros), _folded=folded
    )


def load_feature_table(path: Path) -> FeatureTable:
    """Load a feature table from a plain or gzipped TSV (suffix-detected)."""
    if path.suffix == ".gz":
        with gzip.open(path, "rt", encoding="utf-8") as fh:
            return parse_feature_table(fh.read().splitlines())
    with open(path, encoding="utf-8") as fh:
        return parse_feature_table(fh.read().splitlines())


@dataclass(frozen=True)
class CardIdentity(Generic[K]):
    """One canonical card, keyed however the caller keys cards.

    `key` is `cards.id` when driven from the database and `oracle_id` when
    driven from `parse_cards()` output — the join never cares which.
    `face_names` mirrors `cards.attrs['face_names']`.
    """

    key: K
    name: str
    face_names: Sequence[str] = ()


@dataclass(frozen=True)
class JoinResult(Generic[K]):
    by_card_key: dict[K, Vector]
    matched_exact: int
    matched_folded: int
    matched_via_face: int
    unmatched_cards: tuple[tuple[K, str], ...]
    zero_vector_keys: tuple[K, ...]

    @property
    def matched(self) -> int:
        return len(self.by_card_key)

    def coverage(self, total: int) -> float:
        return self.matched / total if total else 0.0


def join_to_cards(
    table: FeatureTable, cards: Iterable[CardIdentity[K]]
) -> JoinResult[K]:
    """Resolve each card identity to a feature vector.

    Match tiers, in order, first hit wins (mirrors CardResolver's
    exact-then-casefold preference and its full-name-over-face-name rule):

      1. full name, exact
      2. full name, accent/case folded
      3. each face name, exact then folded

    Cards that match nothing are returned in `unmatched_cards` for reporting.
    They are never guessed at, spell-corrected, or fuzzy-matched.
    """
    by_key: dict[K, Vector] = {}
    exact = folded = via_face = 0
    unmatched: list[tuple[K, str]] = []
    zero_keys: list[K] = []
    zero_names = table.zero_vector_names

    for card in cards:
        vector, tier = table.lookup(card.name)
        matched_name = card.name
        if vector is None:
            for face in card.face_names:
                vector, tier = table.lookup(face)
                if vector is not None:
                    matched_name = face
                    via_face += 1
                    break
        if vector is None:
            unmatched.append((card.key, card.name))
            continue
        if tier == "exact" and matched_name == card.name:
            exact += 1
        elif tier == "folded" and matched_name == card.name:
            folded += 1
        by_key[card.key] = vector
        if matched_name in zero_names:
            zero_keys.append(card.key)

    return JoinResult(
        by_card_key=by_key,
        matched_exact=exact,
        matched_folded=folded,
        matched_via_face=via_face,
        unmatched_cards=tuple(unmatched),
        zero_vector_keys=tuple(zero_keys),
    )
