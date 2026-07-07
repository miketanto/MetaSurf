"""Deck recommender — game-neutral decision rules (validated in V-REC).

Consumes only integer/float arrays over a candidate set (the "universe" of
playable options for a format at a point in time): a share vector, a payoff
(matchup) matrix, and per-option overall winrates. Returns indices into that
candidate set. No game-specific ids, names, or modules; no randomness.

The product question is "which deck should I bring?" — a best response to the
*current* field, not a forecast (M3.5 showed the field is not weekly-
predictable; M3.5b showed a best-positioned deck nonetheless wins ~58% of its
real matches). The value decomposes into deck strength (the STRONGEST rule)
plus a small field-positioning bonus (BEST_RESPONSE over STRONGEST); V-REC
measures both against realized match results.

All ties break to the lowest candidate index, so callers that pass their
candidate set in a deterministic order (e.g. sorted archetype id) get
deterministic picks.
"""

from __future__ import annotations

import numpy as np


def field_response_scores(shares: np.ndarray, payoff: np.ndarray) -> np.ndarray:
    """Expected win probability of each candidate against the current field:
    score_a = Σ_b payoff[a, b] · shares[b]. ``payoff[a, b]`` = P(a beats b);
    ``shares`` should sum to ~1 over the candidate set."""
    return payoff @ shares


def best_response_index(shares: np.ndarray, payoff: np.ndarray) -> int:
    """Index of the candidate best positioned against the current field."""
    return int(np.argmax(field_response_scores(shares, payoff)))


def rank_by_best_response(shares: np.ndarray, payoff: np.ndarray) -> np.ndarray:
    """Candidate indices ordered best-positioned first (stable, for the API's
    ranked 'best decks this weekend' list)."""
    return np.argsort(-field_response_scores(shares, payoff), kind="stable")


def most_popular_index(shares: np.ndarray) -> int:
    """Index of the most-played candidate (naive baseline)."""
    return int(np.argmax(shares))


def strongest_index(winrates: np.ndarray) -> int:
    """Index of the highest overall-winrate candidate ('bring a strong deck')."""
    return int(np.argmax(winrates))
