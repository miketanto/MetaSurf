"""Promote-to-rule helper: scaffold a rule file from an emerging cluster's
signature cards, for a human to review and NAME.

This closes the emerging loop (plan §5 Layer 1): detect -> characterize ->
*human names* -> rule -> the named cluster then classifies deterministically
by the rules engine. The scaffold is deliberately incomplete: it fills in the
key-card conditions (the cluster's highest-lift signature cards as
``InMainboard`` conditions, the same condition grammar the ported
MTGOFormatData rules use) but NEVER a name. The ``Name`` field is a loud
placeholder and ``IncludeColorInName`` is left for the human; the system does
not mint archetype names (CLAUDE.md rule 4).

Output is a dict in the exact ported rule-file shape
(``{Name, IncludeColorInName, Conditions:[{Type, Cards:[...]}]}``); the caller
writes it under a format's ``Archetypes/`` dir once a human has renamed it.
"""

from __future__ import annotations

import datetime as dt

import psycopg

from archetypes.emerging import EmergingCluster, SignatureCard

# Loud, invalid-as-a-real-name placeholder. A rule file still carrying this has
# not been named by a human; ``is_named`` / ``assert_named`` reject it so a
# scaffold can never be committed as-is.
NAME_PLACEHOLDER = "RENAME_ME__PROVISIONAL_EMERGING_CLUSTER"

# Only signature cards at least this common in the cluster become defining
# conditions — a card a minority plays is not part of the archetype's identity.
_DEFINING_MIN_IN_FREQ = 0.6
# Cap the number of key-card conditions so the scaffold is a starting point a
# human tightens, not an overfit fingerprint of the sample.
_MAX_CONDITIONS = 6


def is_named(scaffold: dict) -> bool:
    """True once a human has replaced the placeholder Name with a real one."""
    name = scaffold.get("Name")
    return isinstance(name, str) and bool(name.strip()) and name != NAME_PLACEHOLDER


def assert_named(scaffold: dict) -> None:
    """Guard for a promotion pipeline: refuse to persist an unnamed scaffold
    (CLAUDE.md rule 4 — a human names it before it becomes a rule)."""
    if not is_named(scaffold):
        raise ValueError(
            "rule scaffold still carries the provisional placeholder name; a human "
            "must name the archetype before it can be promoted to a rule "
            f"(replace {NAME_PLACEHOLDER!r})"
        )


def _defining_signatures(sigs: tuple[SignatureCard, ...]) -> list[SignatureCard]:
    defining = [s for s in sigs if s.in_cluster_freq >= _DEFINING_MIN_IN_FREQ]
    if not defining:  # fall back to the top signatures if none clears the bar
        defining = list(sigs)
    # highest-lift first is already the stored order; keep it, cap the count
    return defining[:_MAX_CONDITIONS]


def scaffold_from_cluster(
    conn: psycopg.Connection, cluster: EmergingCluster
) -> dict:
    """Build a rule-file scaffold from an in-memory characterized cluster.
    Resolves signature card ids to names via the cards table; a card whose id
    no longer resolves is skipped (never guessed — CLAUDE.md rule 3)."""
    names = _resolve_names(conn, [s.card_id for s in _defining_signatures(cluster.signature_cards)])
    conditions = [
        {"Type": "InMainboard", "Cards": [name]} for name in names if name is not None
    ]
    return _scaffold(conditions, cluster.provisional_descriptor, cluster.n_decks)


def scaffold_from_rollup(
    conn: psycopg.Connection, game: str, format_name: str, as_of: dt.date, cluster_key: int
) -> dict:
    """Build a scaffold from a persisted rollup_emerging cluster (so the loop
    can run off the served feed, not only an in-memory characterization)."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT r.provisional_descriptor, r.n_decks FROM rollup_emerging r"
            " JOIN formats f ON f.id = r.format_id"
            " JOIN games g ON g.id = f.game_id"
            " WHERE g.name = %s AND f.name = %s AND r.as_of = %s AND r.cluster_key = %s",
            (game, format_name, as_of, cluster_key),
        )
        row = cur.fetchone()
        if row is None:
            raise LookupError(
                f"no emerging cluster {cluster_key} for {game}/{format_name} @ {as_of}"
            )
        descriptor, n_decks = row
        cur.execute(
            "SELECT c.name, s.in_cluster_freq FROM rollup_emerging_signature s"
            " JOIN cards c ON c.id = s.card_id"
            " JOIN formats f ON f.id = s.format_id"
            " JOIN games g ON g.id = f.game_id"
            " WHERE g.name = %s AND f.name = %s AND s.as_of = %s AND s.cluster_key = %s"
            " ORDER BY s.rank",
            (game, format_name, as_of, cluster_key),
        )
        sig_rows = cur.fetchall()
    defining = [name for name, in_freq in sig_rows if in_freq >= _DEFINING_MIN_IN_FREQ]
    if not defining:
        defining = [name for name, _ in sig_rows]
    conditions = [{"Type": "InMainboard", "Cards": [name]} for name in defining[:_MAX_CONDITIONS]]
    return _scaffold(conditions, descriptor, n_decks)


def _scaffold(conditions: list[dict], descriptor: str, n_decks: int) -> dict:
    return {
        # NB: placeholder — a human names the archetype (CLAUDE.md rule 4).
        "Name": NAME_PLACEHOLDER,
        "IncludeColorInName": False,
        "Conditions": conditions,
        # provenance so a reviewer sees where the scaffold came from; these
        # underscore keys are ignored by the rule loader (it reads only Name/
        # Conditions/Variants/IncludeColorInName).
        "_provisional_descriptor": descriptor,
        "_source": "emerging-cluster-scaffold",
        "_cluster_n_decks": n_decks,
    }


def _resolve_names(conn: psycopg.Connection, card_ids: list[int]) -> list[str | None]:
    if not card_ids:
        return []
    with conn.cursor() as cur:
        cur.execute("SELECT id, name FROM cards WHERE id = ANY(%s)", (card_ids,))
        by_id: dict[int, str] = dict(cur.fetchall())
    return [by_id.get(cid) for cid in card_ids]
