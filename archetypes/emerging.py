"""Emerging-deck detection + characterization (plan §5 Layer 1 clustering
stage, productized as the §8 S5 feed).

This is the game-specific half of the emerging feature and it lives in
``archetypes/`` on purpose: it imports the validated clustering stack
(``cluster_and_attach``, the vectorizer, the rules engine and its
``deck_color`` / ``_GUILD_NAMES``), none of which ``jobs/`` or ``api/`` may
import (game-neutrality gate). It writes the additive ``rollup_emerging``
tables directly — a game-specific rollup *writer* outside ``jobs/``, the seam
option the handoff sanctioned (see docs/notes for the rationale). The read
side (``api/`` -> ``rollup_emerging``) stays fully game-neutral, symmetric with
how ``jobs/rollups/meta.py`` writes ``rollup_meta`` and the API reads it.

Pipeline, per (format, as_of):

1. **Detect.** Take the decks in ``[as_of - window, as_of]`` that the rules +
   fallback stage does NOT label with a specific rule — the "Rogue/unlabeled
   pool". Vectorize (the validated tf-idf mainboard vectorizer) and run the
   validated ``cluster_and_attach``. Each resulting non-noise cluster of at
   least ``MIN_CLUSTER_DECKS`` decks is a *candidate emerging archetype* — a
   dense new cluster not matching any rule.
2. **Characterize.** Per cluster: signature cards (in-cluster vs out-of-cluster
   mainboard frequency -> lift), color identity (the engine's ``deck_color``
   over the cluster centroid deck, named via ``_GUILD_NAMES``), size,
   first-seen date, recent-window growth, and a winrate if stored match games
   exist for its decks. The PROVISIONAL descriptor = color + top signature card,
   clearly flagged "unnamed / emerging" — never a curated name (CLAUDE.md
   rule 4); a human names it and the promote helper scaffolds a rule.
3. **Persist.** Replace exactly the (format_id, as_of) snapshot of
   ``rollup_emerging`` (+ the signature child rows). Idempotent and
   deterministic: the clustering stage carries no RNG and every ordering here
   is explicit, so re-running writes byte-identical rows.
"""

from __future__ import annotations

import datetime as dt
from collections import Counter
from dataclasses import dataclass

import psycopg

from archetypes.classifier.clustering import NOISE, cluster_and_attach
from archetypes.classifier.corpus import (
    LoadedDeck,
    basic_land_ids,
    load_decks,
    load_definitions,
    rules_label,
)
from archetypes.classifier.engine import _GUILD_NAMES, Deck, deck_color
from archetypes.classifier.vectorizer import vectorize

# Window of trailing days whose Rogue/unlabeled pool is clustered. Matches the
# emergence backtest's "accumulate since a window start" shape; 30 days is long
# enough for a new deck to reach the MIN_CLUSTER_DECKS density but short enough
# that the feed is about *current* arrivals.
WINDOW_DAYS = 30
# Recency sub-window used for the growth signal (fraction of the cluster seen in
# the most recent RECENT_DAYS days).
RECENT_DAYS = 7
# A cluster must have at least this many decks to be a candidate. Equals the
# clustering stage's MIN_CLUSTER_SIZE and the V1.2 emergence acceptance
# criterion (">= 5 appearances"): below this it is noise, not a trend.
MIN_CLUSTER_DECKS = 5
# How many signature cards to keep per cluster (ranked by lift).
TOP_SIGNATURE_CARDS = 8
# Frequency floor so a card unique to the cluster (out-freq 0) gets a finite,
# comparable lift instead of infinity; also the min in-cluster freq to qualify
# as a signature (a card fewer than half the cluster plays is not a signature).
_OUT_FREQ_FLOOR = 0.01
_MIN_SIGNATURE_IN_FREQ = 0.5


@dataclass(frozen=True)
class SignatureCard:
    card_id: int
    in_cluster_freq: float
    out_cluster_freq: float
    lift: float


@dataclass(frozen=True)
class EmergingCluster:
    cluster_key: int  # local within-snapshot HDBSCAN label
    provisional_descriptor: str
    color: str
    deck_ids: tuple[int, ...]
    first_seen: dt.date
    recent_decks: int
    winrate: float | None
    n_match_games: int
    signature_cards: tuple[SignatureCard, ...]

    @property
    def n_decks(self) -> int:
        return len(self.deck_ids)


@dataclass(frozen=True)
class EmergingStats:
    format_id: int
    as_of: dt.date
    n_clusters: int
    rows_written: int

    def summary(self) -> str:
        return (
            f"format {self.format_id} as_of {self.as_of}: "
            f"{self.n_clusters} emerging cluster(s), {self.rows_written} rows"
        )


def color_name(color: str) -> str:
    """Human color-group name for a WUBRG string, reusing the engine's
    ``_GUILD_NAMES`` (the reference GetColorName mapping). Falls back to the
    raw color string for combinations the reference does not name (and
    'Colorless' for the empty/'C' identity)."""
    if color in ("", "C"):
        return "Colorless"
    return _GUILD_NAMES.get(color, color)


def _rogue_pool(
    conn: psycopg.Connection, format_name: str, first: dt.date, as_of: dt.date
) -> list[LoadedDeck]:
    """Decks in the window that the rules+fallback stage does NOT give a
    specific *rule* label — the pool the clustering stage searches for new
    archetypes (the plan's 'unlabeled remainder')."""
    defs, _ = load_definitions(conn, format_name=format_name)
    decks = load_decks(conn, first, as_of, format_name)
    labels = rules_label(decks, defs)
    return [
        d
        for d, c in zip(decks, labels, strict=True)
        if not (c.match is not None and c.match.method == "rules")
    ]


def _signature_cards(
    cluster_ids: list[int],
    all_decks: dict[int, Deck],
    exclude: frozenset[int],
) -> list[SignatureCard]:
    """TF-IDF-style signatures: cards common inside the cluster and rare
    outside it. in_freq/out_freq are mainboard presence rates; lift ranks."""
    cluster_set = set(cluster_ids)
    n_in = len(cluster_ids)
    out_ids = [d for d in all_decks if d not in cluster_set]
    n_out = len(out_ids)

    in_count: Counter[int] = Counter()
    for did in cluster_ids:
        for cid in all_decks[did].main:
            if cid not in exclude:
                in_count[cid] += 1
    out_count: Counter[int] = Counter()
    for did in out_ids:
        for cid in all_decks[did].main:
            if cid not in exclude:
                out_count[cid] += 1

    sigs: list[SignatureCard] = []
    for cid, c in in_count.items():
        in_freq = c / n_in
        if in_freq < _MIN_SIGNATURE_IN_FREQ:
            continue
        out_freq = (out_count.get(cid, 0) / n_out) if n_out else 0.0
        lift = in_freq / max(out_freq, _OUT_FREQ_FLOOR)
        sigs.append(SignatureCard(cid, in_freq, out_freq, lift))
    # deterministic: by lift desc, then in_freq desc, then card_id asc
    sigs.sort(key=lambda s: (-s.lift, -s.in_cluster_freq, s.card_id))
    return sigs[:TOP_SIGNATURE_CARDS]


def _centroid_color(cluster_ids: list[int], decks: dict[int, Deck], defs) -> str:  # type: ignore[no-untyped-def]
    """Color identity of the cluster: the reference ``deck_color`` over a
    centroid deck = the cards present in > half the cluster's mainboards (a
    stable, majority-vote representative rather than any single list)."""
    n = len(cluster_ids)
    present: Counter[int] = Counter()
    for did in cluster_ids:
        for cid in decks[did].main:
            present[cid] += 1
    centroid_main = {cid: 1 for cid, c in present.items() if c > n / 2}
    return deck_color(Deck(main=centroid_main, side={}), defs)


def _cluster_winrate(
    conn: psycopg.Connection, deck_ids: list[int], as_of: dt.date
) -> tuple[float | None, int]:
    """Winrate over decided stored games for the cluster's decks (games on or
    before ``as_of``). ``matches.result`` is ``W-L-D`` from deck_id_a's
    perspective; a cluster deck's games are counted from whichever side it is,
    drawn games excluded from the denominator. Returns (winrate, n_games);
    winrate is None when there are no decided games."""
    if not deck_ids:
        return None, 0
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT m.deck_id_a, m.deck_id_b,
                   split_part(m.result, '-', 1)::int AS w,
                   split_part(m.result, '-', 2)::int AS l
            FROM matches m
            JOIN events e ON e.id = m.event_id
            WHERE e.date <= %s
              AND m.result ~ '^[0-9]+-[0-9]+-[0-9]+$'
              AND (m.deck_id_a = ANY(%s) OR m.deck_id_b = ANY(%s))
            """,
            (as_of, deck_ids, deck_ids),
        )
        rows = cur.fetchall()
    members = set(deck_ids)
    wins = games = 0
    for deck_a, deck_b, w, losses in rows:
        if w == losses:  # drawn match: no decided game evidence
            continue
        a_in = deck_a in members
        b_in = deck_b in members
        if a_in and not b_in:
            wins += 1 if w > losses else 0
            games += 1
        elif b_in and not a_in:
            wins += 1 if losses > w else 0
            games += 1
        # both-in (mirror) contributes no signal about the cluster vs field
    if games == 0:
        return None, 0
    return wins / games, games


def characterize(
    conn: psycopg.Connection,
    format_name: str,
    as_of: dt.date,
    window_days: int = WINDOW_DAYS,
) -> list[EmergingCluster]:
    """Detect + characterize emerging clusters for (format, as_of). Pure read;
    returns the clusters in a deterministic order (by size desc, then
    first_seen, then cluster_key). Writing is done by :func:`build_emerging`."""
    first = as_of - dt.timedelta(days=window_days)
    recent_cutoff = as_of - dt.timedelta(days=RECENT_DAYS)
    defs, _ = load_definitions(conn, format_name=format_name)
    exclude = basic_land_ids(conn)

    pool = _rogue_pool(conn, format_name, first, as_of)
    if len(pool) < MIN_CLUSTER_DECKS:
        return []

    by_id: dict[int, LoadedDeck] = {d.deck_id: d for d in pool}
    decks_main: dict[int, Deck] = {d.deck_id: d.deck for d in pool}
    vectors = vectorize([(d.deck_id, d.deck.main) for d in pool], exclude)
    labels = cluster_and_attach(vectors.matrix)

    members: dict[int, list[int]] = {}
    for did, cl in zip(vectors.deck_ids, labels, strict=True):
        c = int(cl)
        if c != NOISE:
            members.setdefault(c, []).append(did)

    clusters: list[EmergingCluster] = []
    for cluster_key in sorted(members):
        ids = sorted(members[cluster_key])  # deterministic member order
        if len(ids) < MIN_CLUSTER_DECKS:
            continue
        dates = sorted(by_id[i].event_date for i in ids)
        recent = sum(1 for d in dates if d >= recent_cutoff)
        color = _centroid_color(ids, decks_main, defs)
        sigs = _signature_cards(ids, decks_main, exclude)
        winrate, n_games = _cluster_winrate(conn, ids, as_of)
        descriptor = _provisional_descriptor(conn, color, sigs)
        clusters.append(
            EmergingCluster(
                cluster_key=cluster_key,
                provisional_descriptor=descriptor,
                color=color,
                deck_ids=tuple(ids),
                first_seen=dates[0],
                recent_decks=recent,
                winrate=winrate,
                n_match_games=n_games,
                signature_cards=tuple(sigs),
            )
        )
    # size desc, then first_seen asc, then cluster_key asc — stable + reproducible
    clusters.sort(key=lambda c: (-c.n_decks, c.first_seen, c.cluster_key))
    return clusters


def _card_name(conn: psycopg.Connection, card_id: int) -> str | None:
    with conn.cursor() as cur:
        cur.execute("SELECT name FROM cards WHERE id = %s", (card_id,))
        row = cur.fetchone()
    return row[0] if row else None


def _provisional_descriptor(
    conn: psycopg.Connection, color: str, sigs: list[SignatureCard]
) -> str:
    """A clearly-unnamed descriptor: color group + top signature card. NOT a
    curated archetype name — the point is a human still has to name it
    (CLAUDE.md rule 4). The endpoint additionally returns ``named=false``."""
    top = _card_name(conn, sigs[0].card_id) if sigs else None
    label = color_name(color)
    if top:
        label = f"{label} {top}"
    return f"Unnamed: {label}".strip()


def build_emerging(
    conn: psycopg.Connection,
    game_name: str,
    format_name: str,
    as_of: dt.date,
    window_days: int = WINDOW_DAYS,
) -> EmergingStats:
    """Characterize and persist the (format, as_of) emerging snapshot. Replaces
    exactly that snapshot (idempotent); returns write stats."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT f.id FROM formats f JOIN games g ON g.id = f.game_id"
            " WHERE g.name = %s AND f.name = %s",
            (game_name, format_name),
        )
        row = cur.fetchone()
    if row is None:
        raise LookupError(f"unknown game/format: {game_name}/{format_name}")
    format_id = int(row[0])

    clusters = characterize(conn, format_name, as_of, window_days)

    with conn.cursor() as cur:
        cur.execute(
            "DELETE FROM rollup_emerging WHERE format_id = %s AND as_of = %s",
            (format_id, as_of),
        )  # signature child rows cascade
        for c in clusters:
            cur.execute(
                "INSERT INTO rollup_emerging (format_id, as_of, cluster_key,"
                " provisional_descriptor, color, n_decks, first_seen, recent_decks,"
                " winrate, n_match_games) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (
                    format_id,
                    as_of,
                    c.cluster_key,
                    c.provisional_descriptor,
                    c.color,
                    c.n_decks,
                    c.first_seen,
                    c.recent_decks,
                    c.winrate,
                    c.n_match_games,
                ),
            )
            for rank, s in enumerate(c.signature_cards, start=1):
                cur.execute(
                    "INSERT INTO rollup_emerging_signature (format_id, as_of,"
                    " cluster_key, rank, card_id, in_cluster_freq, out_cluster_freq,"
                    " lift) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
                    (
                        format_id,
                        as_of,
                        c.cluster_key,
                        rank,
                        s.card_id,
                        s.in_cluster_freq,
                        s.out_cluster_freq,
                        s.lift,
                    ),
                )
    conn.commit()
    n_rows = sum(1 + len(c.signature_cards) for c in clusters)
    return EmergingStats(format_id, as_of, len(clusters), n_rows)
