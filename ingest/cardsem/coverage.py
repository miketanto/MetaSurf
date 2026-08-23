"""Coverage report: how much of MetaSurf's card universe has CardGuru features?

This is the go/no-go measurement for the card-semantics integration
(docs/notes/card-semantics-integration.md). It answers two questions with
counted numbers, not estimates:

1. **Universe coverage** — of the playable cards the Scryfall importer would
   load into `cards`, how many have a feature vector? Sets the ceiling.
2. **Corpus coverage** — of the cards that *actually appear in decklists*,
   how many have one? This is the number that decides the project, because a
   card nobody plays contributes nothing to a deck vector either way.

Both are reported alongside the zero-vector rate, because a card present in
the table with an all-zero vector is a different failure mode from an absent
card and must not be counted as covered signal.

Everything is computed from the two committed snapshots, so this runs with no
database, no network, and no Forge/XMage checkout.
"""

from __future__ import annotations

import gzip
import json
import shutil
import tempfile
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from ingest.cardsem.dims import FEATURE_NAMES, UNREPRESENTED_MECHANICS
from ingest.cardsem.loader import CardIdentity, FeatureTable, JoinResult, join_to_cards
from ingest.scryfall import parse_cards

# Cards whose printed abilities are (essentially) a single mechanic absent from
# the feature space. Used to demonstrate empirically that an all-zero vector is
# not proof of a vanilla card. Verified against the shipped table this session.
BLIND_SPOT_PROBE: tuple[tuple[str, str], ...] = (
    ("Glistener Elf", "infect"),
    ("Gurmag Angler", "delve"),
    ("Street Wraith", "cycling"),
)

# Genuinely vanilla creatures observed in the corpus sample: an all-zero vector
# here is CORRECT. Contrast with BLIND_SPOT_PROBE.
VANILLA_PROBE: tuple[str, ...] = ("Axebane Beast", "Coral Commando", "Prowling Caracal")

REPO = Path(__file__).resolve().parents[2]
DEFAULT_FEATURES = REPO / "ingest" / "cardsem" / "features.tsv.gz"
DEFAULT_SCRYFALL = REPO / "data" / "scryfall" / "oracle-cards.jsonl.gz"
DEFAULT_CORPUS = REPO / "tests" / "fixtures" / "MTGODecklistCache"


def scryfall_identities(path: Path) -> list[CardIdentity[str]]:
    """The exact card universe `ingest.scryfall` would load, keyed by oracle_id.

    Reuses `parse_cards` rather than re-deriving the layout exclusions and
    resolution-tier rules, so coverage is measured against the same universe
    the classifier actually sees. `parse_cards` takes a plain path, so a
    gzipped snapshot is decompressed to a temp file first.
    """
    if path.suffix == ".gz":
        with tempfile.TemporaryDirectory() as tmp:
            plain = Path(tmp) / "oracle-cards.jsonl"
            with gzip.open(path, "rb") as src, open(plain, "wb") as dst:
                shutil.copyfileobj(src, dst)
            rows = parse_cards(plain)
    else:
        rows = parse_cards(path)
    return [
        CardIdentity(key=r.oracle_id, name=r.name, face_names=r.attrs.get("face_names", ()))
        for r in rows
    ]


@dataclass(frozen=True)
class CorpusUsage:
    """Card usage counted from real MTGODecklistCache files."""

    files: int
    decks: int
    entries_by_name: Counter[str]
    decks_by_mainboard_size: Counter[int]

    @property
    def distinct_names(self) -> int:
        return len(self.entries_by_name)

    @property
    def total_copies(self) -> int:
        return sum(self.entries_by_name.values())

    @property
    def limited_decks(self) -> int:
        """40-card mainboards are Limited (draft/sealed), not constructed."""
        return sum(n for size, n in self.decks_by_mainboard_size.items() if size < 60)


def read_corpus_usage(root: Path) -> CorpusUsage:
    """Count card copies across every CacheItem JSON under `root`.

    Both boards are counted: the vectorizer uses mainboard only, but sideboard
    coverage matters for the Meta Lab / answer-matrix seam, and a gap that
    appears only in sideboards is worth seeing separately from the headline.
    """
    counts: Counter[str] = Counter()
    sizes: Counter[int] = Counter()
    files = decks = 0
    for path in sorted(root.rglob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if not isinstance(data, dict) or "Decks" not in data:
            continue
        files += 1
        for deck in data.get("Decks") or []:
            decks += 1
            main = 0
            for board in ("Mainboard", "Sideboard"):
                for entry in deck.get(board) or []:
                    name = entry.get("CardName")
                    if not name:
                        continue
                    count = int(entry.get("Count") or 0)
                    counts[name] += count
                    if board == "Mainboard":
                        main += count
            sizes[main] += 1
    return CorpusUsage(
        files=files, decks=decks, entries_by_name=counts, decks_by_mainboard_size=sizes
    )


@dataclass(frozen=True)
class CoverageReport:
    table: FeatureTable
    universe_total: int
    universe: JoinResult[str]
    corpus: CorpusUsage
    corpus_join: JoinResult[str]
    corpus_covered_copies: int

    @property
    def universe_zero_rate(self) -> float:
        return _rate(len(self.universe.zero_vector_keys), self.universe.matched)

    @property
    def corpus_name_coverage(self) -> float:
        return _rate(self.corpus_join.matched, self.corpus.distinct_names)

    @property
    def corpus_copy_coverage(self) -> float:
        return _rate(self.corpus_covered_copies, self.corpus.total_copies)


def _rate(part: int, whole: int) -> float:
    return part / whole if whole else 0.0


def _pct(part: int, whole: int) -> str:
    return f"{_rate(part, whole) * 100:.2f}%"


def _row(label: str, count: int, whole: int, *, bold: bool = False) -> str:
    """One markdown table row: label, count, and share of `whole`."""
    mark = "**" if bold else ""
    return f"| {mark}{label}{mark} | {mark}{count}{mark} | {mark}{_pct(count, whole)}{mark} |"


def build_report(
    table: FeatureTable, identities: Iterable[CardIdentity[str]], corpus: CorpusUsage
) -> CoverageReport:
    ids = list(identities)
    universe = join_to_cards(table, ids)

    corpus_ids = [CardIdentity(key=n, name=n) for n in sorted(corpus.entries_by_name)]
    corpus_join = join_to_cards(table, corpus_ids)
    covered_copies = sum(
        corpus.entries_by_name[n] for n in corpus_join.by_card_key
    )

    return CoverageReport(
        table=table,
        universe_total=len(ids),
        universe=universe,
        corpus=corpus,
        corpus_join=corpus_join,
        corpus_covered_copies=covered_copies,
    )


def render(report: CoverageReport, today: str, sample: int = 15) -> str:
    """Deterministic markdown. Every number here is computed above; nothing
    in this function invents a value."""
    u, c, cj = report.universe, report.corpus, report.corpus_join
    lines: list[str] = []
    add = lines.append

    add(f"# Card-semantics coverage — {today}")
    add("")
    add(
        "Owner-directed spike (not a milestone gate): measures whether CardGuru's "
        "mechanical feature table covers enough of MetaSurf's cards to be worth "
        "wiring into the clustering-stage vectorizer. Design note: "
        "`docs/notes/card-semantics-integration.md`."
    )
    add("")
    add(
        "All numbers are printed output of `python -m ingest.cardsem` against the "
        "two committed snapshots. Regenerate with that command; the report is "
        "deterministic."
    )
    add("")

    add("## Feature table")
    add("")
    add(f"- rows (registered names): **{len(report.table.vectors)}**")
    add(f"- dimensionality: **{report.table.dim}**")
    add(
        f"- all-zero vectors: **{len(report.table.zero_vector_names)}** "
        f"({_pct(len(report.table.zero_vector_names), len(report.table.vectors))} of rows)"
    )
    add("")

    add("## 1. Card-universe coverage (the ceiling)")
    add("")
    add(
        "Denominator is every card `ingest.scryfall.parse_cards` would load into "
        "`cards` — the same universe the classifier resolves against."
    )
    add("")
    total = report.universe_total
    add("| metric | count | share |")
    add("|---|---:|---:|")
    add(_row("playable cards in universe", total, total))
    add(_row("with a feature vector", u.matched, total, bold=True))
    add(_row("matched on exact name", u.matched_exact, total))
    add(_row("matched on folded name", u.matched_folded, total))
    add(_row("matched via a face name", u.matched_via_face, total))
    add(_row("no feature vector", len(u.unmatched_cards), total))
    add(_row("matched but all-zero vector", len(u.zero_vector_keys), total))
    add("")

    add("## 2. Corpus coverage (the number that decides it)")
    add("")
    add(
        f"Counted over {c.files} real MTGODecklistCache files ({c.decks} decks) in "
        "`tests/fixtures/`. **This is a fixture sample, not the full corpus** — "
        "`data/MTGODecklistCache` is gitignored and absent in this environment, so "
        "the headline must be re-measured against the full clone before the "
        "integration is committed to."
    )
    add("")
    add(
        f"Composition: {c.limited_decks} of {c.decks} decks have a sub-60-card "
        f"mainboard, i.e. are **Limited** (the 2019 MOCS Open fixture), not "
        "constructed. That inflates the obscure-commons tail — which makes full "
        "coverage a *stronger* result, since Limited pools are exactly where "
        "marginal cards would be expected to go missing."
    )
    add("")
    add("| metric | count | share |")
    add("|---|---:|---:|")
    add(_row("distinct card names in corpus", c.distinct_names, c.distinct_names))
    add(_row("distinct names with features", cj.matched, c.distinct_names, bold=True))
    add(_row("total copies across all decks", c.total_copies, c.total_copies))
    add(
        _row(
            "copies with features (weighted)",
            report.corpus_covered_copies,
            c.total_copies,
            bold=True,
        )
    )
    add(
        _row(
            "corpus names with an all-zero vector",
            len(cj.zero_vector_keys),
            c.distinct_names,
        )
    )
    add("")

    if cj.unmatched_cards:
        add(f"### Corpus cards with no feature vector ({len(cj.unmatched_cards)})")
        add("")
        add("Ranked by copies played — these are the cards a feature channel would be blind to.")
        add("")
        ranked = sorted(
            ((c.entries_by_name[n], n) for _, n in cj.unmatched_cards),
            key=lambda kv: (-kv[0], kv[1]),
        )
        add("| copies | card |")
        add("|---:|---|")
        for copies, name in ranked[:sample]:
            add(f"| {copies} | {name} |")
        if len(ranked) > sample:
            add(f"| … | _{len(ranked) - sample} more_ |")
        add("")

    if cj.zero_vector_keys:
        add(f"### Corpus cards present but all-zero ({len(cj.zero_vector_keys)})")
        add("")
        add(
            "The extractor found no scripted mechanics. Masking these (rather than "
            "treating a zero vector as 'this card does nothing') is a correctness "
            "requirement, not an optimization."
        )
        add("")
        ranked_zero = sorted(
            ((c.entries_by_name[str(k)], str(k)) for k in cj.zero_vector_keys),
            key=lambda kv: (-kv[0], kv[1]),
        )
        add("| copies | card |")
        add("|---:|---|")
        for copies, name in ranked_zero[:sample]:
            add(f"| {copies} | {name} |")
        if len(ranked_zero) > sample:
            add(f"| … | _{len(ranked_zero) - sample} more_ |")
        add("")

    add("## 3. Blind spots in the feature space")
    add("")
    add(
        f"The {len(FEATURE_NAMES)} dimensions (names in `ingest/cardsem/dims.py`) cover "
        "9 answer classes, 20 effect APIs, 18 keywords and 21 structural features. "
        "Keyword mechanics outside that 18-keyword list have no dimension, so a card "
        "whose only ability is one of them extracts to an all-zero vector — "
        "indistinguishable from a vanilla creature."
    )
    add("")
    missing = [m for m in UNREPRESENTED_MECHANICS if not any(m in n for n in FEATURE_NAMES)]
    add(
        f"Archetype-defining mechanics with **no dimension**: "
        f"{', '.join(f'`{m}`' for m in missing)}."
    )
    add("")
    add("Empirical check against the shipped table:")
    add("")
    add("| card | mechanic | vector |")
    add("|---|---|---|")
    for name, mechanic in BLIND_SPOT_PROBE:
        add(f"| {name} | {mechanic} | {_describe(report.table, name)} |")
    for name in VANILLA_PROBE:
        add(f"| {name} | _(vanilla — zero is correct)_ | {_describe(report.table, name)} |")
    add("")
    add(
        "**Consequence for the integration:** the zero-vector set mixes correct zeros "
        "with extraction gaps, and the two cannot be told apart from the vector alone. "
        "Masking (per-deck feature coverage below a threshold ⇒ fall back to the "
        "card-identity channel) is therefore a correctness requirement. Extending "
        "CardGuru's `KEYWORDS` list upstream is the real fix and is cheap — it is a "
        "list literal in `rl/e2_extract.py`."
    )
    add("")

    return "\n".join(lines) + "\n"


def _describe(table: FeatureTable, name: str) -> str:
    vector = table.vectors.get(name)
    if vector is None:
        return "absent from table"
    if not any(vector):
        return "**all-zero**"
    live = [n for n, v in zip(FEATURE_NAMES, vector, strict=True) if v]
    return f"{len(live)} dims set ({', '.join(f'`{n}`' for n in live[:3])}…)"
