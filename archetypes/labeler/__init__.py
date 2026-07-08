"""Batch archetype labeling: classify the stored corpus and persist labels.

Writes, for every Modern deck with at least one deck_cards row:
- an `archetype_labels` row (deck_id, archetype_id, classifier_version,
  method, confidence) — the full relabeling history (plan §4 schema);
- `decks.archetype_id` + `decks.classifier_version` for the same version.

Archetype identity granularity is a parameter:
- ``"parent"`` (default): the rule/fallback file's `Name`; variant matches
  collapse to their parent archetype — the identity V1 validated against.
- ``"variant"``: the classifier's full display label — rule variant AND color
  group (guild/shard/wedge) where the definition opts in via
  ``IncludeColorInName``. Examples: Eldrazi -> Broodscale / Ramp Eldrazi;
  Energy -> "Boros Energy" / "Mardu Energy"; Blink -> "Esper Blink" /
  "Jeskai Blink". Each split label is linked to its base archetype via
  ``archetypes.parent_id`` (plan §4 split seam). The variant/color rules are
  the ported rule files, not new hand-authored ones. NB: V1's per-archetype F1
  was measured at parent granularity; this finer product granularity owes its
  own validation pass before it's a validated claim.
Decks matched by no rule and no fallback get the reserved `Rogue` archetype —
the plan's "outliers are Rogue" semantics (§5 Layer 1). The clustering stage
is deliberately NOT part of batch labeling: it exists to flag candidate new
archetypes for human naming (the emerging-deck feature), not to mint
archetype ids, and rules+fallbacks label ~99% of the corpus (measured in the
run summary).

Deterministic: decks are classified in deck-id order month by month, the
engine carries no randomness, and archetype rows are inserted in sorted-name
order; re-running for the same classifier_version replaces its labels
idempotently.
"""

from __future__ import annotations

import datetime as dt
from collections import Counter
from dataclasses import dataclass, field

import psycopg

from archetypes.classifier.corpus import load_decks, load_definitions
from archetypes.classifier.engine import base_display_name, classify

ROGUE_NAME = "Rogue"

METHOD_RULES = "rules"
METHOD_FALLBACK = "fallback"
METHOD_ROGUE = "rogue"


@dataclass
class LabelStats:
    classifier_version: str = ""
    decks_labeled: int = 0
    by_method: Counter = field(default_factory=Counter)
    conflicts: int = 0
    archetypes_total: int = 0
    decks_without_cards: int = 0  # not labeled: nothing to classify
    by_archetype: Counter = field(default_factory=Counter)

    def summary(self) -> str:
        lines = [
            f"classifier_version:      {self.classifier_version}",
            f"decks labeled:           {self.decks_labeled}",
            "  by method:             "
            + ", ".join(f"{m}={n}" for m, n in sorted(self.by_method.items())),
            f"  rule conflicts:        {self.conflicts} (resolved PreferSimpler)",
            f"archetypes rows:         {self.archetypes_total}",
            f"decks without cards:     {self.decks_without_cards} (unlabeled)",
            "top archetypes:          "
            + ", ".join(f"{a}={n}" for a, n in self.by_archetype.most_common(10)),
        ]
        return "\n".join(lines)


def _month_starts(start: dt.date, end: dt.date) -> list[dt.date]:
    out = []
    cur = dt.date(start.year, start.month, 1)
    while cur <= end:
        out.append(cur)
        cur = (
            dt.date(cur.year + 1, 1, 1)
            if cur.month == 12
            else dt.date(cur.year, cur.month + 1, 1)
        )
    return out


def _corpus_range(conn: psycopg.Connection, format_name: str) -> tuple[dt.date, dt.date] | None:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT min(e.date), max(e.date) FROM events e
            JOIN formats f ON f.id = e.format_id AND f.name = %s
            """,
            (format_name,),
        )
        row = cur.fetchone()
    if row is None or row[0] is None:
        return None
    return row[0], row[1]


def _upsert_archetypes(
    conn: psycopg.Connection,
    format_name: str,
    names: set[str],
    parent_of: dict[str, str] | None = None,
) -> dict[str, int]:
    """Insert missing archetypes rows (sorted-name order for deterministic ids
    on a fresh database) and return name -> id. When ``parent_of`` maps a
    variant name to its parent name, set ``archetypes.parent_id`` accordingly
    (plan §4 split seam); the parent row is inserted too if unseen."""
    parent_of = parent_of or {}
    all_names = set(names) | set(parent_of.values())
    with conn.cursor() as cur:
        cur.execute("SELECT id FROM formats WHERE name = %s", (format_name,))
        row = cur.fetchone()
        assert row is not None, f"format {format_name!r} not seeded"
        format_id = row[0]
        for name in sorted(all_names):
            cur.execute(
                """
                INSERT INTO archetypes (format_id, name)
                VALUES (%s, %s) ON CONFLICT (format_id, name) DO NOTHING
                """,
                (format_id, name),
            )
        cur.execute("SELECT name, id FROM archetypes WHERE format_id = %s", (format_id,))
        name_to_id: dict[str, int] = dict(cur.fetchall())
        for child, parent in sorted(parent_of.items()):
            cur.execute(
                "UPDATE archetypes SET parent_id = %s"
                " WHERE id = %s AND parent_id IS DISTINCT FROM %s",
                (name_to_id[parent], name_to_id[child], name_to_id[parent]),
            )
    return name_to_id


def label_corpus(
    conn: psycopg.Connection,
    format_name: str = "modern",
    granularity: str = "parent",
) -> LabelStats:
    """Classify every stored deck of the format and persist labels.

    ``granularity``: "parent" (V1-validated identity, default) or "variant"
    (a matched variant is its own archetype under ``parent_id``)."""
    if granularity not in ("parent", "variant"):
        raise ValueError(f"granularity must be 'parent' or 'variant', got {granularity!r}")
    stats = LabelStats()
    defs, _report = load_definitions(conn, format_name=format_name)
    stats.classifier_version = defs.classifier_version

    span = _corpus_range(conn, format_name)
    if span is None:
        raise RuntimeError(f"no events for format {format_name!r} — run the import first")

    rows: list[tuple[int, str, str, float | None]] = []  # deck_id, name, method, confidence
    parent_of: dict[str, str] = {}  # variant name -> parent name (variant granularity)
    for month in _month_starts(*span):
        month_end = (
            dt.date(month.year + 1, 1, 1)
            if month.month == 12
            else dt.date(month.year, month.month + 1, 1)
        ) - dt.timedelta(days=1)
        for loaded in load_decks(conn, month, month_end, format_name):
            c = classify(loaded.deck, defs)
            if c.conflict:
                stats.conflicts += 1
            if c.match is None:
                rows.append((loaded.deck_id, ROGUE_NAME, METHOD_ROGUE, None))
                continue
            name = c.match.archetype
            if granularity == "variant":
                # the classifier's full display label: rule variant + color
                # group where the definition opts in via IncludeColorInName
                # (e.g. Energy -> "Boros Energy" / "Mardu Energy"; Eldrazi ->
                # "Broodscale"). Link each split label to its base archetype.
                name = c.match.label
                base = base_display_name(c.match.archetype)
                if name != base:
                    parent_of[name] = base
            if c.match.method == METHOD_RULES:
                rows.append((loaded.deck_id, name, METHOD_RULES, 1.0))
            else:
                rows.append((loaded.deck_id, name, METHOD_FALLBACK, c.match.similarity))

    name_to_id = _upsert_archetypes(
        conn, format_name, {name for _, name, _, _ in rows}, parent_of
    )
    stats.archetypes_total = len(name_to_id)

    with conn.cursor() as cur:
        # idempotent per classifier_version: replace this version's labels
        cur.execute(
            "DELETE FROM archetype_labels WHERE classifier_version = %s",
            (defs.classifier_version,),
        )
        with cur.copy(
            "COPY archetype_labels (deck_id, archetype_id, classifier_version,"
            " method, confidence) FROM STDIN"
        ) as copy:
            for deck_id, name, method, confidence in rows:
                copy.write_row(
                    (deck_id, name_to_id[name], defs.classifier_version, method, confidence)
                )
        cur.execute(
            """
            CREATE TEMP TABLE _label_updates
                (deck_id bigint PRIMARY KEY, archetype_id integer) ON COMMIT DROP
            """
        )
        with cur.copy("COPY _label_updates (deck_id, archetype_id) FROM STDIN") as copy:
            for deck_id, name, _method, _confidence in rows:
                copy.write_row((deck_id, name_to_id[name]))
        cur.execute(
            """
            UPDATE decks d SET archetype_id = u.archetype_id, classifier_version = %s
            FROM _label_updates u WHERE u.deck_id = d.id
            """,
            (defs.classifier_version,),
        )

    stats.decks_labeled = len(rows)
    for _deck_id, name, method, _conf in rows:
        stats.by_method[method] += 1
        stats.by_archetype[name] += 1

    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT count(*) FROM decks d
            JOIN events e ON e.id = d.event_id
            JOIN formats f ON f.id = e.format_id AND f.name = %s
            WHERE NOT EXISTS (SELECT 1 FROM deck_cards dc WHERE dc.deck_id = d.id)
            """,
            (format_name,),
        )
        stats.decks_without_cards = cur.fetchone()[0]  # type: ignore[index]
    conn.commit()

    _post_label_checks(conn, format_name, defs.classifier_version, stats)
    return stats


def _post_label_checks(
    conn: psycopg.Connection, format_name: str, version: str, stats: LabelStats
) -> None:
    """DQ gates: fail loudly instead of persisting a partial labeling."""
    problems: list[str] = []
    with conn.cursor() as cur:
        cur.execute(
            "SELECT count(*) FROM archetype_labels WHERE classifier_version = %s",
            (version,),
        )
        (n_labels,) = cur.fetchone()  # type: ignore[misc]
        if n_labels != stats.decks_labeled:
            problems.append(f"label rows {n_labels} != decks labeled {stats.decks_labeled}")
        cur.execute(
            """
            SELECT count(*) FROM decks d
            JOIN events e ON e.id = d.event_id
            JOIN formats f ON f.id = e.format_id AND f.name = %s
            WHERE d.archetype_id IS NULL
              AND EXISTS (SELECT 1 FROM deck_cards dc WHERE dc.deck_id = d.id)
            """,
            (format_name,),
        )
        (n_unlabeled,) = cur.fetchone()  # type: ignore[misc]
        if n_unlabeled:
            problems.append(f"{n_unlabeled} non-empty decks left without archetype_id")
        cur.execute(
            """
            SELECT count(*) FROM archetype_labels al
            LEFT JOIN archetypes a ON a.id = al.archetype_id
            WHERE al.classifier_version = %s AND a.id IS NULL
            """,
            (version,),
        )
        (n_orphan,) = cur.fetchone()  # type: ignore[misc]
        if n_orphan:
            problems.append(f"{n_orphan} labels reference missing archetypes")
    if problems:
        raise RuntimeError("post-labeling data-quality checks FAILED:\n" + "\n".join(problems))
