"""Emerging-deck feed rollup (plan §8 S5): candidate new archetypes.

Revision ID: 0003
Revises: 0002
Create Date: 2026-07-08

Additive only (plan §4.3). Snapshot-keyed by format_id + as_of like the other
rollups, so a nightly job appends a new snapshot without mutating old ones;
re-running for the same (format_id, as_of) replaces exactly that snapshot.

A row of ``rollup_emerging`` is a dense cluster of Rogue/unlabeled decks that
does not match any rule — a *candidate* emerging archetype awaiting a human
name (CLAUDE.md rule 4: the system never mints archetype names). Its
``provisional_descriptor`` is a clearly-unnamed color + top-signature-card
label, never a curated name. The per-cluster signature cards (the TF-IDF-style
in-cluster-vs-out lift that a human uses to name and, via the promote helper,
scaffold a rule from) live in the child table ``rollup_emerging_signature``.

``cluster_key`` identifies the cluster *within one snapshot* (the local
integer HDBSCAN label); it is not stable across snapshots and is used only to
join the two tables and give the endpoint a deterministic ordering handle.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "rollup_emerging",
        sa.Column("format_id", sa.Integer, sa.ForeignKey("formats.id"), nullable=False),
        sa.Column("as_of", sa.Date, nullable=False),
        # local, within-snapshot cluster handle (HDBSCAN label); NOT stable
        # across snapshots — joins to the signature child table only
        sa.Column("cluster_key", sa.Integer, nullable=False),
        # PROVISIONAL descriptor only (color + top signature card), flagged
        # unnamed — a human names emerging decks (CLAUDE.md rule 4)
        sa.Column("provisional_descriptor", sa.Text, nullable=False),
        # WUBRG color identity string of the cluster centroid deck ('' = colorless)
        sa.Column("color", sa.Text, nullable=False),
        sa.Column("n_decks", sa.Integer, nullable=False),
        sa.Column("first_seen", sa.Date, nullable=False),
        # growth: decks in the most recent 7 days of the window / total
        sa.Column("recent_decks", sa.Integer, nullable=False),
        # cluster winrate over decided stored games, NULL when no match data
        sa.Column("winrate", sa.Float, nullable=True),
        sa.Column("n_match_games", sa.Integer, nullable=False),
        sa.PrimaryKeyConstraint("format_id", "as_of", "cluster_key"),
    )
    # per-cluster signature cards: highest in-cluster-vs-out lift, ranked
    op.create_table(
        "rollup_emerging_signature",
        sa.Column("format_id", sa.Integer, sa.ForeignKey("formats.id"), nullable=False),
        sa.Column("as_of", sa.Date, nullable=False),
        sa.Column("cluster_key", sa.Integer, nullable=False),
        sa.Column("rank", sa.Integer, nullable=False),
        sa.Column("card_id", sa.Integer, sa.ForeignKey("cards.id"), nullable=False),
        # fraction of the cluster's decks that play the card (mainboard)
        sa.Column("in_cluster_freq", sa.Float, nullable=False),
        # fraction of out-of-cluster decks that play it
        sa.Column("out_cluster_freq", sa.Float, nullable=False),
        # lift = in_cluster_freq / max(out_cluster_freq, floor) — the signal
        sa.Column("lift", sa.Float, nullable=False),
        sa.PrimaryKeyConstraint("format_id", "as_of", "cluster_key", "rank"),
        sa.ForeignKeyConstraint(
            ["format_id", "as_of", "cluster_key"],
            ["rollup_emerging.format_id", "rollup_emerging.as_of", "rollup_emerging.cluster_key"],
            ondelete="CASCADE",
        ),
    )


def downgrade() -> None:
    op.drop_table("rollup_emerging_signature")
    op.drop_table("rollup_emerging")
