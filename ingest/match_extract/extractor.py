"""Match extraction: Rounds in cached source files -> canonical `matches` rows.

Written strictly against the observed schema (docs/notes/
mtgodecklistcache-observed-schema.md, "Rounds/Matches deep-dive") and the real
fixtures under tests/fixtures/MTGODecklistCache/. Observed facts this code
relies on (all verified by executed scans, none assumed):

- Match objects are exactly {Player1, Player2, Result}; Result is always
  `W-L-D` **from Player1's perspective** (verified via 10,175 bracket
  advancements and swiss-vs-standings win reconciliation).
- mtgo challenges carry Top-8 bracket rounds only; melee/manatraders carry
  full swiss; topdeck uses bare numeric round names and match-level results
  (`1-0-0`/`0-0-1`); leagues/prelims have Rounds null.
- Byes appear as Player2 null (manatraders) or "" (topdeck). A bye is not a
  pairing: skipped and counted, never a match row.
- Players are matched to decks by exact `Player` string. Standings-only
  players exist (deck_id_b is nullable); a player name held by more than one
  deck in the same event is ambiguous and is never guessed (counted, side
  left unresolved).
- 2 corpus-wide mirrored duplicate rows (a drawn match recorded once per
  orientation in the same round) -> per-round unordered-pair dedup.

League 5-0 data must NEVER feed winrates (winner-censored): leagues carry no
Rounds in the observed corpus, and a league event that suddenly does is an
anomaly that fails the run loudly rather than ingesting garbage.

Stored orientation: `matches.result` is always from deck_id_a's perspective.
When only Player2's deck is resolvable the players are swapped and the result
inverted (W-L-D -> L-W-D) so deck_id_a is never null.

Deterministic: events are processed in id order, rounds/matches in file
order, and the run replaces all previously extracted matches (matches is
derived data; raw files stay the source of truth).
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

import orjson
import psycopg

BATCH_EVENTS = 200

_RE_MATCH_RESULT = re.compile(r"^(\d+)-(\d+)-(\d+)$")


@dataclass(frozen=True)
class ParsedResult:
    wins: int
    losses: int
    draws: int

    def canonical(self) -> str:
        return f"{self.wins}-{self.losses}-{self.draws}"

    def inverted(self) -> ParsedResult:
        return ParsedResult(self.losses, self.wins, self.draws)


def parse_match_result(raw: str | None) -> ParsedResult | None:
    """Parse a Rounds match Result (`W-L-D`, Player1's perspective)."""
    if not raw:
        return None
    m = _RE_MATCH_RESULT.match(raw)
    if not m:
        return None
    return ParsedResult(int(m.group(1)), int(m.group(2)), int(m.group(3)))


@dataclass
class ExtractStats:
    events_seen: int = 0
    events_without_rounds: int = 0
    events_with_rounds: int = 0
    matches_seen: int = 0
    matches_inserted: int = 0
    byes_skipped: int = 0
    self_matches_skipped: int = 0
    duplicates_skipped: int = 0
    invalid_results_skipped: int = 0
    matches_both_sides_unresolved: int = 0
    sides_swapped: int = 0
    deck_b_unresolved: int = 0
    unmatched_player_slots: int = 0
    ambiguous_player_slots: int = 0
    by_source: Counter = field(default_factory=Counter)
    unmatched_by_source: Counter = field(default_factory=Counter)

    def summary(self) -> str:
        lines = [
            f"events seen:                {self.events_seen}",
            f"  without rounds:           {self.events_without_rounds}",
            f"  with rounds:              {self.events_with_rounds}",
            f"match entries seen:         {self.matches_seen}",
            f"matches inserted:           {self.matches_inserted}",
            f"  byes skipped:             {self.byes_skipped}",
            f"  duplicates skipped:       {self.duplicates_skipped}",
            f"  self-matches skipped:     {self.self_matches_skipped}",
            f"  invalid results skipped:  {self.invalid_results_skipped}",
            f"  both sides unresolved:    {self.matches_both_sides_unresolved}",
            f"  sides swapped (a<->b):    {self.sides_swapped}",
            f"  deck_id_b null:           {self.deck_b_unresolved}",
            "DQ — unmatched player slots: "
            f"{self.unmatched_player_slots}"
            f" (ambiguous: {self.ambiguous_player_slots}); by source: "
            + ", ".join(f"{s}={n}" for s, n in sorted(self.unmatched_by_source.items())),
            "events with rounds by source: "
            + ", ".join(f"{s}={n}" for s, n in sorted(self.by_source.items())),
        ]
        return "\n".join(lines)


def _deck_map(cur: psycopg.Cursor, event_id: int) -> tuple[dict[str, int], set[str]]:
    """Exact Player -> deck_id for the event; names on more than one deck are
    ambiguous and returned separately (never guessed)."""
    cur.execute(
        "SELECT player, id FROM decks WHERE event_id = %s AND player IS NOT NULL"
        " ORDER BY id",
        (event_id,),
    )
    mapping: dict[str, int] = {}
    ambiguous: set[str] = set()
    for player, deck_id in cur.fetchall():
        if player in mapping or player in ambiguous:
            ambiguous.add(player)
            mapping.pop(player, None)
        else:
            mapping[player] = deck_id
    return mapping, ambiguous


def _extract_event(
    event_id: int,
    source: str,
    rounds: list,
    deck_map: dict[str, int],
    ambiguous: set[str],
    stats: ExtractStats,
) -> list[tuple[int, str, int, int | None, str]]:
    rows: list[tuple[int, str, int, int | None, str]] = []
    for rnd in rounds:
        round_name = rnd.get("RoundName")
        seen_pairs: set[frozenset[str]] = set()
        for m in rnd.get("Matches") or []:
            stats.matches_seen += 1
            p1, p2 = m.get("Player1"), m.get("Player2")
            result = parse_match_result(m.get("Result"))
            if result is None:
                stats.invalid_results_skipped += 1
                continue
            if not p1 or not p2:
                # observed byes: Player2 null (manatraders) or "" (topdeck)
                stats.byes_skipped += 1
                continue
            if p1 == p2:
                stats.self_matches_skipped += 1
                continue
            pair = frozenset((p1, p2))
            if pair in seen_pairs:
                stats.duplicates_skipped += 1
                continue
            seen_pairs.add(pair)

            for player in (p1, p2):
                if player not in deck_map:
                    stats.unmatched_player_slots += 1
                    stats.unmatched_by_source[source] += 1
                    if player in ambiguous:
                        stats.ambiguous_player_slots += 1

            deck_a = deck_map.get(p1)
            deck_b = deck_map.get(p2)
            if deck_a is None and deck_b is None:
                stats.matches_both_sides_unresolved += 1
                continue
            if deck_a is None:
                # store from the resolvable side's perspective
                deck_a, deck_b = deck_b, None
                result = result.inverted()
                stats.sides_swapped += 1
            if deck_b is None:
                stats.deck_b_unresolved += 1
            assert deck_a is not None
            rows.append((event_id, round_name, deck_a, deck_b, result.canonical()))
    return rows


def extract_matches(conn: psycopg.Connection, cache_root: Path) -> ExtractStats:
    """Extract matches for every stored event from its cached raw file.

    Replaces all previously extracted matches (derived data, rebuildable
    from the raw archive at any time).
    """
    stats = ExtractStats()
    with conn.cursor() as cur:
        cur.execute("DELETE FROM matches")
        cur.execute(
            "SELECT id, source, event_type, raw_ref FROM events"
            " WHERE raw_ref IS NOT NULL ORDER BY id"
        )
        events = cur.fetchall()

        batch: list[tuple[int, str, int, int | None, str]] = []
        pending = 0
        for event_id, source, event_type, raw_ref in events:
            stats.events_seen += 1
            raw = orjson.loads((cache_root / raw_ref).read_bytes())
            rounds = raw.get("Rounds") or []
            if not rounds:
                stats.events_without_rounds += 1
                continue
            if event_type is not None and "league" in event_type:
                # winner-censored source suddenly carrying pairings: source
                # structure changed -> stop, never feed league data to winrates
                raise RuntimeError(
                    f"league event {raw_ref!r} has non-empty Rounds — "
                    "contradicts observed schema; refusing to extract"
                )
            stats.events_with_rounds += 1
            stats.by_source[source] += 1
            deck_map, ambiguous = _deck_map(cur, event_id)
            batch.extend(
                _extract_event(event_id, source, rounds, deck_map, ambiguous, stats)
            )
            pending += 1
            if pending >= BATCH_EVENTS:
                _copy_rows(cur, batch)
                stats.matches_inserted += len(batch)
                batch, pending = [], 0
        if batch:
            _copy_rows(cur, batch)
            stats.matches_inserted += len(batch)
    conn.commit()
    run_post_extract_checks(conn, stats)
    return stats


def _copy_rows(
    cur: psycopg.Cursor, rows: list[tuple[int, str, int, int | None, str]]
) -> None:
    with cur.copy(
        "COPY matches (event_id, round, deck_id_a, deck_id_b, result) FROM STDIN"
    ) as copy:
        for row in rows:
            copy.write_row(row)


def run_post_extract_checks(conn: psycopg.Connection, stats: ExtractStats) -> None:
    """DQ gates (CLAUDE.md testing rule 6): fail loudly on referential or
    semantic anomalies instead of feeding them to the winrate model."""
    problems: list[str] = []
    with conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM matches")
        (n,) = cur.fetchone()  # type: ignore[misc]
        if n != stats.matches_inserted:
            problems.append(f"matches rows {n} != inserted count {stats.matches_inserted}")
        cur.execute(
            """
            SELECT count(*) FROM matches m JOIN events e ON e.id = m.event_id
            WHERE e.event_type LIKE '%%league%%'
            """
        )
        (n_league,) = cur.fetchone()  # type: ignore[misc]
        if n_league:
            problems.append(f"{n_league} matches attached to league events")
        cur.execute(r"SELECT count(*) FROM matches WHERE result !~ '^\d+-\d+-\d+$'")
        (n_bad,) = cur.fetchone()  # type: ignore[misc]
        if n_bad:
            problems.append(f"{n_bad} matches with malformed result")
        cur.execute(
            """
            SELECT count(*) FROM matches m
            JOIN decks a ON a.id = m.deck_id_a
            LEFT JOIN decks b ON b.id = m.deck_id_b
            WHERE a.event_id <> m.event_id
               OR (b.id IS NOT NULL AND b.event_id <> m.event_id)
            """
        )
        (n_cross,) = cur.fetchone()  # type: ignore[misc]
        if n_cross:
            problems.append(f"{n_cross} matches referencing decks of another event")
        cur.execute("SELECT count(*) FROM matches WHERE deck_id_a = deck_id_b")
        (n_self,) = cur.fetchone()  # type: ignore[misc]
        if n_self:
            problems.append(f"{n_self} matches pairing a deck against itself")
    if problems:
        raise RuntimeError("post-extraction data-quality checks FAILED:\n" + "\n".join(problems))
