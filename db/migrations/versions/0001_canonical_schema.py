"""canonical schema (plan §4)

Revision ID: 0001
Revises:
Create Date: 2026-07-07

All entities carry the game dimension from day one. Additive-only.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "games",
        sa.Column("id", sa.Integer, sa.Identity(), primary_key=True),
        sa.Column("name", sa.Text, nullable=False, unique=True),
    )
    op.create_table(
        "formats",
        sa.Column("id", sa.Integer, sa.Identity(), primary_key=True),
        sa.Column("game_id", sa.Integer, sa.ForeignKey("games.id"), nullable=False),
        sa.Column("name", sa.Text, nullable=False),
        sa.Column("config", JSONB, nullable=False, server_default="{}"),
        sa.UniqueConstraint("game_id", "name"),
    )
    op.create_table(
        "cards",
        sa.Column("id", sa.BigInteger, sa.Identity(), primary_key=True),
        sa.Column("game_id", sa.Integer, sa.ForeignKey("games.id"), nullable=False),
        # game-specific canonical identity; for MTG this is the Scryfall oracle_id
        sa.Column("canonical_ref", sa.Text, nullable=False),
        sa.Column("name", sa.Text, nullable=False),
        sa.Column("attrs", JSONB, nullable=False, server_default="{}"),
        sa.UniqueConstraint("game_id", "canonical_ref"),
    )
    op.create_index("ix_cards_game_name", "cards", ["game_id", "name"])
    op.create_table(
        "events",
        sa.Column("id", sa.BigInteger, sa.Identity(), primary_key=True),
        sa.Column("game_id", sa.Integer, sa.ForeignKey("games.id"), nullable=False),
        sa.Column("source", sa.Text, nullable=False),
        sa.Column("source_event_id", sa.Text, nullable=False),
        sa.Column("format_id", sa.Integer, sa.ForeignKey("formats.id"), nullable=False),
        sa.Column("name", sa.Text, nullable=True),
        sa.Column("date", sa.Date, nullable=False),
        sa.Column("event_type", sa.Text, nullable=True),
        sa.Column("player_count", sa.Integer, nullable=True),
        sa.Column("raw_ref", sa.Text, nullable=True),
        sa.UniqueConstraint("source", "source_event_id"),
    )
    op.create_index("ix_events_format_date", "events", ["format_id", "date"])
    op.create_table(
        "archetypes",
        sa.Column("id", sa.Integer, sa.Identity(), primary_key=True),
        sa.Column("format_id", sa.Integer, sa.ForeignKey("formats.id"), nullable=False),
        sa.Column("name", sa.Text, nullable=False),
        sa.Column("status", sa.Text, nullable=False, server_default="active"),
        sa.Column("parent_id", sa.Integer, sa.ForeignKey("archetypes.id"), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint("format_id", "name"),
    )
    op.create_table(
        "decks",
        sa.Column("id", sa.BigInteger, sa.Identity(), primary_key=True),
        sa.Column("event_id", sa.BigInteger, sa.ForeignKey("events.id"), nullable=False),
        sa.Column("player", sa.Text, nullable=True),
        sa.Column("finish_rank", sa.Integer, nullable=True),
        sa.Column("wins", sa.Integer, nullable=True),
        sa.Column("losses", sa.Integer, nullable=True),
        sa.Column("draws", sa.Integer, nullable=True),
        sa.Column("archetype_id", sa.Integer, sa.ForeignKey("archetypes.id"), nullable=True),
        sa.Column("classifier_version", sa.Text, nullable=True),
    )
    op.create_index("ix_decks_event", "decks", ["event_id"])
    op.create_table(
        "deck_cards",
        sa.Column(
            "deck_id",
            sa.BigInteger,
            sa.ForeignKey("decks.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("card_id", sa.BigInteger, sa.ForeignKey("cards.id"), nullable=False),
        sa.Column("count", sa.Integer, nullable=False),
        # board zone names are per-game config (MTG: main/side)
        sa.Column("board", sa.Text, nullable=False),
        sa.PrimaryKeyConstraint("deck_id", "card_id", "board"),
    )
    op.create_index("ix_deck_cards_card", "deck_cards", ["card_id"])
    op.create_table(
        "matches",
        sa.Column("id", sa.BigInteger, sa.Identity(), primary_key=True),
        sa.Column("event_id", sa.BigInteger, sa.ForeignKey("events.id"), nullable=False),
        sa.Column("round", sa.Text, nullable=True),
        sa.Column("deck_id_a", sa.BigInteger, sa.ForeignKey("decks.id"), nullable=False),
        sa.Column("deck_id_b", sa.BigInteger, sa.ForeignKey("decks.id"), nullable=True),
        sa.Column("result", sa.Text, nullable=True),
    )
    op.create_index("ix_matches_event", "matches", ["event_id"])
    op.create_table(
        "archetype_labels",
        sa.Column(
            "deck_id",
            sa.BigInteger,
            sa.ForeignKey("decks.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("archetype_id", sa.Integer, sa.ForeignKey("archetypes.id"), nullable=False),
        sa.Column("classifier_version", sa.Text, nullable=False),
        sa.Column("method", sa.Text, nullable=True),
        sa.Column("confidence", sa.Float, nullable=True),
        sa.PrimaryKeyConstraint("deck_id", "classifier_version"),
    )
    # operational: unresolved card names per ingestion run (never guessed, always logged)
    op.create_table(
        "ingest_unresolved_cards",
        sa.Column("id", sa.BigInteger, sa.Identity(), primary_key=True),
        sa.Column("game_id", sa.Integer, sa.ForeignKey("games.id"), nullable=False),
        sa.Column("format_id", sa.Integer, sa.ForeignKey("formats.id"), nullable=False),
        sa.Column("card_name", sa.Text, nullable=False),
        sa.Column("occurrences", sa.Integer, nullable=False),
        sa.Column("decks_affected", sa.Integer, nullable=False),
        sa.UniqueConstraint("game_id", "format_id", "card_name"),
    )


def downgrade() -> None:
    for table in (
        "ingest_unresolved_cards",
        "archetype_labels",
        "matches",
        "deck_cards",
        "decks",
        "archetypes",
        "events",
        "cards",
        "formats",
        "games",
    ):
        op.drop_table(table)
