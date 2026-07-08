"""Game-neutral seam for BUILDING the emerging-deck feed.

The read side (``GET /emerging``) needs no seam: it serves the precomputed
``rollup_emerging`` tables like any other rollup, and stays game-neutral. The
*build* side is the wrinkle — detecting emerging clusters runs the game's
clustering stage + rules engine + card resolver (``archetypes/``), which the
gated packages may not import (game-neutrality CI gate). This is the exact
shape of the classify wrinkle (``api/classifier.py``): a Protocol here, a game
adapter implementing it (``archetypes/emerging_service.py``), injected outside
the gated packages by the composition root.

Symmetry with the other rollups: ``jobs/rollups/*`` write their tables and are
game-neutral because they only touch persisted canonical tables + game-neutral
models. The emerging writer cannot be game-neutral (it clusters card vectors),
so it lives on the game side of this Protocol instead of in ``jobs/``. The
nightly entrypoint depends on the Protocol only.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Protocol

import psycopg


@dataclass(frozen=True)
class EmergingBuildStats:
    format_id: int
    as_of: dt.date
    n_clusters: int
    rows_written: int

    def summary(self) -> str:
        return (
            f"format {self.format_id} as_of {self.as_of}: "
            f"{self.n_clusters} emerging cluster(s), {self.rows_written} rows"
        )


class EmergingBuilder(Protocol):
    def build_emerging(
        self,
        conn: psycopg.Connection,
        game: str,
        format_name: str,
        as_of: dt.date,
    ) -> EmergingBuildStats:
        """Detect + characterize + persist the (format, as_of) emerging
        snapshot into the rollup_emerging tables. Idempotent per snapshot.
        Raises LookupError on an unknown game/format."""
        ...
