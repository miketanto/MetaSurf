"""MTG implementation of the read API's EmergingBuilder Protocol.

Thin adapter: it delegates to :func:`archetypes.emerging.build_emerging` (the
validated clustering-stage characterizer + rollup writer) and maps its stats
onto the game-neutral ``EmergingBuildStats`` DTO the API package defines. Wired
in by the composition root (``serve.py`` / the rollup entrypoint), outside the
game-neutrality-gated packages.
"""

from __future__ import annotations

import datetime as dt

import psycopg

from api.emerging import EmergingBuildStats
from archetypes.emerging import build_emerging


class MtgEmergingBuilder:
    def build_emerging(
        self,
        conn: psycopg.Connection,
        game: str,
        format_name: str,
        as_of: dt.date,
    ) -> EmergingBuildStats:
        stats = build_emerging(conn, game, format_name, as_of)
        return EmergingBuildStats(
            format_id=stats.format_id,
            as_of=stats.as_of,
            n_clusters=stats.n_clusters,
            rows_written=stats.rows_written,
        )
