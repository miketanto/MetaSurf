"""M5 rollup tables (plan §4: analytics jobs -> precomputed rollups -> read API).

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-07

Additive only (plan §4.3). Snapshot tables are keyed by format_id + as_of so a
nightly job appends a new snapshot without mutating old ones; re-running a job
for the same (format_id, as_of) replaces exactly that snapshot (idempotent).
Rollup tables are contracts with clients: columns are only ever added.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # S1 meta snapshot: trailing-window share + shrunk winrate per archetype
    op.create_table(
        "rollup_meta",
        sa.Column("format_id", sa.Integer, sa.ForeignKey("formats.id"), nullable=False),
        sa.Column("as_of", sa.Date, nullable=False),
        sa.Column("archetype_id", sa.Integer, sa.ForeignKey("archetypes.id"), nullable=False),
        sa.Column("share", sa.Float, nullable=False),
        sa.Column("winrate", sa.Float, nullable=False),
        sa.Column("wr_ci_lo", sa.Float, nullable=False),
        sa.Column("wr_ci_hi", sa.Float, nullable=False),
        sa.Column("n_decks", sa.Integer, nullable=False),
        sa.PrimaryKeyConstraint("format_id", "as_of", "archetype_id"),
    )
    # S2 matchup matrix: one row per ordered archetype pair in the snapshot
    op.create_table(
        "rollup_matchups",
        sa.Column("format_id", sa.Integer, sa.ForeignKey("formats.id"), nullable=False),
        sa.Column("as_of", sa.Date, nullable=False),
        sa.Column("arch_a", sa.Integer, sa.ForeignKey("archetypes.id"), nullable=False),
        sa.Column("arch_b", sa.Integer, sa.ForeignKey("archetypes.id"), nullable=False),
        sa.Column("p_a_beats_b", sa.Float, nullable=False),
        sa.Column("ci_lo", sa.Float, nullable=False),
        sa.Column("ci_hi", sa.Float, nullable=False),
        # raw stored matches between the pair (both orientations), undecayed
        sa.Column("n_matches", sa.Integer, nullable=False),
        sa.PrimaryKeyConstraint("format_id", "as_of", "arch_a", "arch_b"),
    )
    # S3 premium series: weekly share/winrate history per archetype
    op.create_table(
        "rollup_archetype_ts",
        sa.Column("format_id", sa.Integer, sa.ForeignKey("formats.id"), nullable=False),
        sa.Column("archetype_id", sa.Integer, sa.ForeignKey("archetypes.id"), nullable=False),
        # Sat..Fri bucket keyed by its Saturday (the V3 panel convention)
        sa.Column("week", sa.Date, nullable=False),
        sa.Column("share", sa.Float, nullable=False),
        sa.Column("winrate", sa.Float, nullable=False),
        sa.Column("wr_ci_lo", sa.Float, nullable=False),
        sa.Column("wr_ci_hi", sa.Float, nullable=False),
        sa.Column("n_decks", sa.Integer, nullable=False),
        sa.PrimaryKeyConstraint("format_id", "archetype_id", "week"),
    )
    op.create_index(
        "ix_rollup_archetype_ts_format_week", "rollup_archetype_ts", ["format_id", "week"]
    )
    # S2/S6 ranked best-positioned list (V-REC best response to the field)
    op.create_table(
        "rollup_best_decks",
        sa.Column("format_id", sa.Integer, sa.ForeignKey("formats.id"), nullable=False),
        sa.Column("as_of", sa.Date, nullable=False),
        sa.Column("rank", sa.Integer, nullable=False),
        sa.Column("archetype_id", sa.Integer, sa.ForeignKey("archetypes.id"), nullable=False),
        sa.Column("exp_winrate_vs_field", sa.Float, nullable=False),
        sa.PrimaryKeyConstraint("format_id", "as_of", "rank"),
    )
    # S4 recent-results feed (denormalized so the API never touches fact tables)
    op.create_table(
        "rollup_events",
        sa.Column("format_id", sa.Integer, sa.ForeignKey("formats.id"), nullable=False),
        sa.Column("event_id", sa.BigInteger, sa.ForeignKey("events.id"), nullable=False),
        sa.Column("date", sa.Date, nullable=False),
        sa.Column("name", sa.Text, nullable=True),
        sa.Column("source", sa.Text, nullable=False),
        sa.Column("player_count", sa.Integer, nullable=True),
        sa.Column("top_archetype_id", sa.Integer, sa.ForeignKey("archetypes.id"), nullable=True),
        sa.PrimaryKeyConstraint("format_id", "event_id"),
    )
    op.create_index("ix_rollup_events_format_date", "rollup_events", ["format_id", "date"])


def downgrade() -> None:
    for table in (
        "rollup_events",
        "rollup_best_decks",
        "rollup_archetype_ts",
        "rollup_matchups",
        "rollup_meta",
    ):
        op.drop_table(table)
