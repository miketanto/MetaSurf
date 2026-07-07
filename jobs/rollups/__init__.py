"""M5 rollup jobs (plan §4: analytics jobs -> precomputed rollup tables).

Each module builds one ``rollup_*`` table from the canonical tables by
calling the validated game-neutral model functions. The read API serves
these tables only; nothing here runs at request time.

Game-neutral (plan §4.1 rule 2, enforced by scripts/check_game_neutrality.py):
jobs receive (game, format) as names, resolve them to canonical ids, and
operate on ids from there. Deterministic: no randomness, no wall-clock reads,
all iteration in sorted order — re-running a job for the same ``as_of``
reproduces the snapshot byte-identically.
"""

from jobs.rollups.archetype_ts import build_archetype_ts
from jobs.rollups.best_decks import build_best_decks
from jobs.rollups.events import build_events
from jobs.rollups.matchups import build_matchups
from jobs.rollups.meta import build_meta

__all__ = [
    "build_archetype_ts",
    "build_best_decks",
    "build_events",
    "build_matchups",
    "build_meta",
]
