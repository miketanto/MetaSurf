"""DB -> weekly panels for the V3 evolution suites.

Series construction (protocol frozen from executed inspection queries before
any model ran; numbers quoted in the V3 report):

- Weeks are Sat..Fri buckets keyed by their Saturday. The forecast target is
  the WEEKEND (Sat+Sun) value — "next weekend's meta share" per plan V3.1 —
  so the series compares like with like weekend populations.
- Meta share of archetype a in week w = labeled weekend decks of a / all
  labeled weekend decks (144/144 Saturdays 2022-07..2025-03 have >= 189
  such decks; zero gaps). Absent archetypes carry literal 0 — their true
  share.
- Card series (V3.3): mean mainboard copies per labeled weekend deck,
  denominator = all labeled weekend decks of the week (decks without the
  card count as 0 copies) — the format-wide tech-drift signal.
- Latent winrates (coupling input) come from the frozen Layer-2 model
  fitted as of each Saturday on matches strictly before it — no leakage
  by construction.

Everything is loaded in deterministic (id-sorted) order.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

import numpy as np
import psycopg

from models.winrate import WinrateModel
from validation.v2_winrates.data import load_match_data, n_archetype_slots


@dataclass(frozen=True)
class WeeklyPanel:
    """entity_ids[i] labels panel row i; saturdays[j] labels column j."""

    saturdays: list[dt.date]
    entity_ids: np.ndarray
    values: np.ndarray  # (n_entities, n_weeks) float
    counts: np.ndarray | None = None  # raw per-cell counts where meaningful

    @property
    def n_weeks(self) -> int:
        return len(self.saturdays)


def _saturday_index(first_sat: dt.date, last_sat: dt.date) -> tuple[list[dt.date], dict]:
    assert first_sat.isoweekday() == 6 and last_sat.isoweekday() == 6
    sats: list[dt.date] = []
    d = first_sat
    while d <= last_sat:
        sats.append(d)
        d += dt.timedelta(days=7)
    return sats, {s: i for i, s in enumerate(sats)}


def load_share_panel(
    conn: psycopg.Connection,
    format_name: str,
    first_sat: dt.date,
    last_sat: dt.date,
) -> tuple[WeeklyPanel, np.ndarray]:
    """Weekend share panel over all archetypes seen in the window, plus the
    per-week total labeled weekend deck counts (the share denominators)."""
    sats, sat_idx = _saturday_index(first_sat, last_sat)
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT date_trunc('week', e.date - 5)::date + 5 AS sat,
                   d.archetype_id, count(*)
            FROM decks d
            JOIN events e ON e.id = d.event_id
            JOIN formats f ON f.id = e.format_id AND f.name = %s
            WHERE d.archetype_id IS NOT NULL
              AND extract(isodow FROM e.date) IN (6, 7)
              AND e.date BETWEEN %s AND %s
            GROUP BY 1, 2 ORDER BY 1, 2
            """,
            (format_name, first_sat, last_sat + dt.timedelta(days=1)),
        )
        rows = cur.fetchall()
    ids = np.array(sorted({r[1] for r in rows}), dtype=np.int64)
    id_idx = {int(a): i for i, a in enumerate(ids)}
    counts = np.zeros((len(ids), len(sats)))
    for sat, arch, n in rows:
        counts[id_idx[int(arch)], sat_idx[sat]] = n
    totals = counts.sum(axis=0)
    with np.errstate(invalid="ignore", divide="ignore"):
        shares = np.where(totals > 0, counts / np.where(totals > 0, totals, 1.0), 0.0)
    return WeeklyPanel(saturdays=sats, entity_ids=ids, values=shares, counts=counts), totals


def load_card_copies_panel(
    conn: psycopg.Connection,
    format_name: str,
    first_sat: dt.date,
    last_sat: dt.date,
) -> WeeklyPanel:
    """Mean mainboard copies per labeled weekend deck, per card per week."""
    sats, sat_idx = _saturday_index(first_sat, last_sat)
    board_zone = "main"
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT date_trunc('week', e.date - 5)::date + 5 AS sat, count(*)
            FROM decks d
            JOIN events e ON e.id = d.event_id
            JOIN formats f ON f.id = e.format_id AND f.name = %s
            WHERE d.archetype_id IS NOT NULL
              AND extract(isodow FROM e.date) IN (6, 7)
              AND e.date BETWEEN %s AND %s
            GROUP BY 1
            """,
            (format_name, first_sat, last_sat + dt.timedelta(days=1)),
        )
        totals = np.zeros(len(sats))
        for sat, n in cur.fetchall():
            totals[sat_idx[sat]] = n
        cur.execute(
            """
            SELECT date_trunc('week', e.date - 5)::date + 5 AS sat,
                   dc.card_id, sum(dc.count)
            FROM deck_cards dc
            JOIN decks d ON d.id = dc.deck_id
            JOIN events e ON e.id = d.event_id
            JOIN formats f ON f.id = e.format_id AND f.name = %s
            WHERE dc.board = %s
              AND d.archetype_id IS NOT NULL
              AND extract(isodow FROM e.date) IN (6, 7)
              AND e.date BETWEEN %s AND %s
            GROUP BY 1, 2 ORDER BY 1, 2
            """,
            (format_name, board_zone, first_sat, last_sat + dt.timedelta(days=1)),
        )
        rows = cur.fetchall()
    ids = np.array(sorted({r[1] for r in rows}), dtype=np.int64)
    id_idx = {int(c): i for i, c in enumerate(ids)}
    copies = np.zeros((len(ids), len(sats)))
    for sat, card, total_copies in rows:
        copies[id_idx[int(card)], sat_idx[sat]] = float(total_copies)
    with np.errstate(invalid="ignore", divide="ignore"):
        mean_copies = np.where(totals > 0, copies / np.where(totals > 0, totals, 1.0), 0.0)
    return WeeklyPanel(saturdays=sats, entity_ids=ids, values=mean_copies)


def latent_winrate_panel(
    conn: psycopg.Connection,
    format_name: str,
    entity_ids: np.ndarray,
    saturdays: list[dt.date],
) -> np.ndarray:
    """Layer-2 posterior mean winrate per archetype as of each Saturday
    (fitted on matches strictly before it). Shape (len(entity_ids), n_weeks)."""
    data, names, _stats = load_match_data(conn, format_name)
    n = n_archetype_slots(names)
    model = WinrateModel()
    out = np.full((len(entity_ids), len(saturdays)), np.nan)
    for j, sat in enumerate(saturdays):
        post = model.fit(data, sat.toordinal(), n)
        mean = post.archetype_mean()
        out[:, j] = mean[entity_ids]
    return out
