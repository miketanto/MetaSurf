"""Shared data access for the V1 validation suites.

The implementation moved to archetypes.classifier.corpus in M2 so that the
production batch labeler can use the same loaders without importing
validation code; this module re-exports the original names unchanged.
"""

from archetypes.classifier.corpus import (
    LoadedDeck,
    basic_land_ids,
    load_decks,
    load_definitions,
    rules_label,
)

__all__ = [
    "LoadedDeck",
    "basic_land_ids",
    "load_decks",
    "load_definitions",
    "rules_label",
]
