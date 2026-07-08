"""One-shot importer: MTGODecklistCache clone -> canonical schema.

Deterministic by construction: files are walked in sorted order, card lines are
sorted, ids are drawn from fresh sequences, and duplicate events (same
(source, filename-stem) — observed re-publications, identical deck sets) are
skipped first-wins on the sorted path order.
"""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

import psycopg

from ingest.formats_config import FormatConfig, load_formats
from ingest.normalize.cache_item import NormalizedEvent, detect_format, normalize_file
from ingest.normalize.resolver import CardResolver

BATCH_FILES = 500
# Live sources date next-day league instances across the UTC<->US day boundary;
# a real completed event can legitimately read one day ahead of the ingesting
# host. Beyond this small window a future date means a parse error (garbage),
# which the DQ gate must still reject.
FUTURE_DATE_TOLERANCE_DAYS = 2


@dataclass
class ImportStats:
    files_seen: int = 0
    files_imported: int = 0
    files_skipped_format_unknown: int = 0
    files_skipped_other_format: int = 0
    files_skipped_duplicate: int = 0
    files_skipped_existing: int = 0
    events: int = 0
    decks: int = 0
    deck_card_rows: int = 0
    unresolved_names: int = 0
    unresolved_occurrences: int = 0
    decks_with_unresolved: int = 0
    standings_only_players: int = 0
    zero_count_card_lines: int = 0
    by_source: Counter = field(default_factory=Counter)

    def summary(self) -> str:
        lines = [
            f"files seen:                 {self.files_seen}",
            f"files imported:             {self.files_imported}",
            f"  skipped (format unknown): {self.files_skipped_format_unknown}",
            f"  skipped (other format):   {self.files_skipped_other_format}",
            f"  skipped (duplicate):      {self.files_skipped_duplicate}",
            f"  skipped (already in db):  {self.files_skipped_existing}",
            f"events inserted:            {self.events}",
            f"decks inserted:             {self.decks}",
            f"deck_cards rows:            {self.deck_card_rows}",
            f"unresolved card names:      {self.unresolved_names}"
            f" ({self.unresolved_occurrences} occurrences,"
            f" {self.decks_with_unresolved} decks affected)",
            f"standings-only players:     {self.standings_only_players}",
            f"zero-count card lines:      {self.zero_count_card_lines} (dropped)",
            "imported files by source:   "
            + ", ".join(f"{s}={n}" for s, n in sorted(self.by_source.items())),
        ]
        return "\n".join(lines)


def seed_games_and_formats(conn: psycopg.Connection, formats: list[FormatConfig]) -> None:
    """Idempotent seed of games/formats rows from config."""
    with conn.cursor() as cur:
        for game in sorted({f.game for f in formats}):
            cur.execute(
                "INSERT INTO games (name) VALUES (%s) ON CONFLICT (name) DO NOTHING",
                (game,),
            )
        for fmt in formats:
            cur.execute(
                """
                INSERT INTO formats (game_id, name, config)
                SELECT g.id, %s, %s::jsonb FROM games g WHERE g.name = %s
                ON CONFLICT (game_id, name) DO UPDATE SET config = EXCLUDED.config
                """,
                (fmt.name, json.dumps(fmt.config_jsonb), fmt.game),
            )
    conn.commit()


def discover_files(
    cache_root: Path,
    tokens_by_format: dict[str, tuple[str, ...]],
    target_formats: set[str],
    stats: ImportStats,
    existing: set[tuple[str, str]] | None = None,
) -> list[tuple[Path, str, str]]:
    """Sorted, deduplicated (path, source, format) list for the target formats.

    `existing` is a set of (source, source_event_id) already in the events
    table; matching files are skipped and counted (incremental daily ingestion,
    M4). events dedupe on (source, source_event_id) — the filename stem is the
    source_event_id — so this keeps a re-run additive instead of colliding on
    the events unique constraint.
    """
    already = existing or set()
    tournaments = cache_root / "Tournaments"
    files = sorted(tournaments.glob("*/*/*/*/*.json"))
    seen: set[tuple[str, str]] = set()
    out: list[tuple[Path, str, str]] = []
    for path in files:
        stats.files_seen += 1
        source = path.relative_to(tournaments).parts[0]
        fmt = detect_format(path.name, tokens_by_format)
        if fmt is None:
            stats.files_skipped_format_unknown += 1
            continue
        if fmt not in target_formats:
            stats.files_skipped_other_format += 1
            continue
        key = (source, path.stem)
        if key in seen:
            stats.files_skipped_duplicate += 1
            continue
        if key in already:
            stats.files_skipped_existing += 1
            continue
        seen.add(key)
        out.append((path, source, fmt))
    return out


def _nextvals(cur: psycopg.Cursor, table: str, n: int) -> list[int]:
    cur.execute(
        "SELECT nextval(pg_get_serial_sequence(%s, 'id')) FROM generate_series(1, %s)",
        (table, n),
    )
    return [r[0] for r in cur.fetchall()]


def _insert_batch(
    conn: psycopg.Connection,
    batch: list[tuple[NormalizedEvent, str]],
    game_id: int,
    format_ids: dict[str, int],
    resolver: CardResolver,
    unresolved: dict[tuple[str, str], list[int]],
    stats: ImportStats,
) -> None:
    """COPY one batch of normalized events. unresolved maps
    (format, name) -> [occurrences, decks_affected]."""
    with conn.cursor() as cur:
        event_ids = _nextvals(cur, "events", len(batch))
        deck_count = sum(len(ev.decks) for ev, _ in batch)
        deck_ids = _nextvals(cur, "decks", deck_count)

        with cur.copy(
            "COPY events (id, game_id, source, source_event_id, format_id, name,"
            " date, event_type, player_count, raw_ref) FROM STDIN"
        ) as copy:
            for eid, (ev, fmt) in zip(event_ids, batch, strict=True):
                copy.write_row(
                    (
                        eid,
                        game_id,
                        ev.source,
                        ev.source_event_id,
                        format_ids[fmt],
                        ev.name,
                        ev.event_date,
                        ev.event_type,
                        ev.player_count,
                        ev.raw_ref,
                    )
                )

        deck_rows = []
        card_rows = []
        i = 0
        for eid, (ev, fmt) in zip(event_ids, batch, strict=True):
            stats.standings_only_players += ev.standings_only_players
            stats.zero_count_card_lines += ev.zero_count_card_lines
            for deck in ev.decks:
                did = deck_ids[i]
                i += 1
                deck_rows.append(
                    (did, eid, deck.player, deck.finish_rank, deck.wins, deck.losses, deck.draws)
                )
                missing_in_deck: set[str] = set()
                for line in deck.cards:
                    cid = resolver.resolve(line.name)
                    if cid is None:
                        unresolved.setdefault((fmt, line.name), [0, 0])[0] += 1
                        missing_in_deck.add(line.name)
                    else:
                        card_rows.append((did, cid, line.count, line.board))
                for name in missing_in_deck:
                    unresolved[(fmt, name)][1] += 1
                if missing_in_deck:
                    stats.decks_with_unresolved += 1

        with cur.copy(
            "COPY decks (id, event_id, player, finish_rank, wins, losses, draws) FROM STDIN"
        ) as copy:
            for row in deck_rows:
                copy.write_row(row)
        # aggregate duplicates that resolve to the same card_id within a board
        # (e.g. a face name and its full name both mapping to one oracle card)
        agg: dict[tuple[int, int, str], int] = {}
        for did, cid, count, board in card_rows:
            agg[(did, cid, board)] = agg.get((did, cid, board), 0) + count
        with cur.copy("COPY deck_cards (deck_id, card_id, count, board) FROM STDIN") as copy:
            for (did, cid, board), count in sorted(agg.items()):
                copy.write_row((did, cid, count, board))

        stats.events += len(batch)
        stats.decks += len(deck_rows)
        stats.deck_card_rows += len(agg)
    conn.commit()


def run_import(
    conn: psycopg.Connection,
    cache_root: Path,
    game: str = "mtg",
    only_formats: set[str] | None = None,
    skip_existing: bool = False,
) -> ImportStats:
    stats = ImportStats()
    formats = [f for f in load_formats() if f.game == game]
    seed_games_and_formats(conn, formats)

    targets = {f.name for f in formats if f.do_import}
    if only_formats is not None:
        targets &= only_formats
    tokens_by_format = {f.name: f.slug_tokens for f in formats}

    with conn.cursor() as cur:
        cur.execute("SELECT id FROM games WHERE name = %s", (game,))
        row = cur.fetchone()
        assert row is not None
        game_id = row[0]
        cur.execute(
            "SELECT name, id FROM formats WHERE game_id = %s",
            (game_id,),
        )
        format_ids: dict[str, int] = dict(cur.fetchall())

    resolver = CardResolver.from_db(conn, game)
    if len(resolver) == 0:
        raise RuntimeError(
            "cards table is empty — run the card ingestion first "
            "(all deck cards would be unresolved)"
        )

    existing: set[tuple[str, str]] | None = None
    if skip_existing:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT source, source_event_id FROM events e"
                " JOIN formats f ON f.id = e.format_id WHERE f.game_id = %s",
                (game_id,),
            )
            existing = {(s, sid) for s, sid in cur.fetchall()}

    files = discover_files(cache_root, tokens_by_format, targets, stats, existing)
    unresolved: dict[tuple[str, str], list[int]] = {}
    batch: list[tuple[NormalizedEvent, str]] = []
    for path, source, fmt in files:
        ev = normalize_file(path, cache_root, source)
        batch.append((ev, fmt))
        stats.files_imported += 1
        stats.by_source[source] += 1
        if len(batch) >= BATCH_FILES:
            _insert_batch(conn, batch, game_id, format_ids, resolver, unresolved, stats)
            batch = []
    if batch:
        _insert_batch(conn, batch, game_id, format_ids, resolver, unresolved, stats)

    _write_unresolved(conn, game_id, format_ids, unresolved, stats)
    run_post_import_checks(conn, stats)
    return stats


def _write_unresolved(
    conn: psycopg.Connection,
    game_id: int,
    format_ids: dict[str, int],
    unresolved: dict[tuple[str, str], list[int]],
    stats: ImportStats,
) -> None:
    stats.unresolved_names = len(unresolved)
    stats.unresolved_occurrences = sum(v[0] for v in unresolved.values())
    with conn.cursor() as cur:
        for (fmt, name), (occurrences, decks_affected) in sorted(unresolved.items()):
            cur.execute(
                """
                INSERT INTO ingest_unresolved_cards
                    (game_id, format_id, card_name, occurrences, decks_affected)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (game_id, format_id, card_name)
                DO UPDATE SET
                    occurrences = ingest_unresolved_cards.occurrences + EXCLUDED.occurrences,
                    decks_affected = ingest_unresolved_cards.decks_affected
                        + EXCLUDED.decks_affected
                """,
                (game_id, format_ids[fmt], name, occurrences, decks_affected),
            )
    conn.commit()


def run_post_import_checks(conn: psycopg.Connection, stats: ImportStats) -> None:
    """Data-quality gates (CLAUDE.md testing rule 6): fail loudly instead of
    ingesting garbage."""
    problems: list[str] = []
    with conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM events")
        (n_events,) = cur.fetchone()  # type: ignore[misc]
        cur.execute("SELECT count(*) FROM decks")
        (n_decks,) = cur.fetchone()  # type: ignore[misc]
        if n_events == 0 or n_decks == 0:
            problems.append(f"row-count sanity failed: events={n_events} decks={n_decks}")
        # Live MTGO dates a league by its run-day instance, which is legitimately
        # up to a day ahead of the ingesting host's current_date across the
        # UTC<->US day boundary (verified 2026-07-08: modern-league-2026-07-08,
        # 58 real 5-0 lists, ingested at 2026-07-07 19:38 America/Chicago). A
        # genuine garbage date (parse error) is years off, far beyond this
        # tolerance, so the gate still catches garbage while accepting real
        # boundary events. Frozen-corpus behaviour is unchanged (no historical
        # event is within the tolerance of "today").
        cur.execute(
            "SELECT count(*) FROM events WHERE date > current_date + %s::int",
            (FUTURE_DATE_TOLERANCE_DAYS,),
        )
        (n_future,) = cur.fetchone()  # type: ignore[misc]
        if n_future:
            problems.append(
                f"{n_future} events dated more than {FUTURE_DATE_TOLERANCE_DAYS} "
                "days in the future"
            )
        cur.execute(
            """
            SELECT count(*) FROM decks d
            LEFT JOIN events e ON e.id = d.event_id WHERE e.id IS NULL
            """
        )
        (n_orphan,) = cur.fetchone()  # type: ignore[misc]
        if n_orphan:
            problems.append(f"{n_orphan} orphaned decks")
        cur.execute("SELECT count(*) FROM deck_cards WHERE count < 1")
        (n_zero,) = cur.fetchone()  # type: ignore[misc]
        if n_zero:
            problems.append(f"{n_zero} deck_cards rows with count < 1")
    if problems:
        raise RuntimeError("post-import data-quality checks FAILED:\n" + "\n".join(problems))
