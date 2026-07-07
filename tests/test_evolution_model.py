"""Evolution-model tests: the panel builders run on the real fixture corpus
via the real pipeline (CLAUDE.md forbids synthetic-only model tests), and the
Holt/coupling functions carry exact-property tests on hand-built series in
addition.
"""

from __future__ import annotations

import datetime as dt

import numpy as np
import orjson
import pytest

from archetypes.labeler import label_corpus
from ingest.cache_import.importer import run_import
from ingest.match_extract import extract_matches
from models.evolution import (
    fit_coupling,
    holt_forecast,
    holt_forecast_panel,
    holt_forecast_path,
)
from tests.conftest import FIXTURES
from validation.v3_evolution.data import load_card_copies_panel, load_share_panel

pytestmark = pytest.mark.db


def _fixture_card_names() -> set[str]:
    names: set[str] = set()
    for path in sorted((FIXTURES / "Tournaments").glob("*/*/*/*/*.json")):
        data = orjson.loads(path.read_bytes())
        for deck in data.get("Decks") or []:
            for zone in ("Mainboard", "Sideboard"):
                for entry in deck.get(zone) or []:
                    names.add(entry["CardName"])
    return names


@pytest.fixture(scope="module")
def fixture_db(test_db_url):
    import psycopg

    with psycopg.connect(test_db_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "TRUNCATE ingest_unresolved_cards, archetype_labels, matches, deck_cards,"
                " decks, events, archetypes, cards RESTART IDENTITY CASCADE"
            )
            cur.execute("INSERT INTO games (name) VALUES ('mtg') ON CONFLICT DO NOTHING")
            cur.execute("SELECT id FROM games WHERE name = 'mtg'")
            game_id = cur.fetchone()[0]
            names = sorted(_fixture_card_names())
            cur.executemany(
                "INSERT INTO cards (game_id, canonical_ref, name) VALUES (%s, %s, %s)",
                [(game_id, f"test-ref:{i}", n) for i, n in enumerate(names)],
            )
        conn.commit()
        run_import(conn, FIXTURES)
        label_corpus(conn)
        extract_matches(conn, FIXTURES)
        yield conn


def test_share_panel_from_real_fixtures(fixture_db):
    # window covering the 2022-10-08 melee Dallas fixture (a Saturday event)
    panel, totals = load_share_panel(
        fixture_db, "modern", dt.date(2022, 10, 1), dt.date(2022, 10, 29)
    )
    assert panel.n_weeks == 5
    dallas = panel.saturdays.index(dt.date(2022, 10, 8))
    assert totals[dallas] > 0
    # shares sum to 1 where decks exist, 0 elsewhere
    sums = panel.values.sum(axis=0)
    assert np.isclose(sums[dallas], 1.0)
    for j, t in enumerate(totals):
        if t == 0:
            assert sums[j] == 0.0
    # counts reconcile with the share denominators
    assert panel.counts is not None
    assert np.isclose(panel.counts[:, dallas].sum(), totals[dallas])


def test_card_panel_from_real_fixtures(fixture_db):
    panel = load_card_copies_panel(
        fixture_db, "modern", dt.date(2022, 10, 1), dt.date(2022, 10, 29)
    )
    dallas = panel.saturdays.index(dt.date(2022, 10, 8))
    # mean mainboard copies per deck: positive somewhere, bounded by 4x deck size
    assert panel.values[:, dallas].max() > 0
    assert panel.values.max() < 100
    # weeks with no decks are all-zero columns
    assert panel.values[:, 0].max() == 0.0


def test_holt_variants_agree_on_real_series(fixture_db):
    panel, _totals = load_share_panel(
        fixture_db, "modern", dt.date(2022, 10, 1), dt.date(2022, 10, 29)
    )
    y = panel.values  # real, if sparse, series
    single = np.array([holt_forecast(row, 0.6, 0.1) for row in y])
    vectorized = holt_forecast_panel(y, 0.6, 0.1)
    assert np.allclose(single, vectorized)
    path = holt_forecast_path(y, 0.6, 0.1)
    # path's final column equals the forecast made from all but the last column
    assert np.allclose(path[:, -1], holt_forecast_panel(y[:, :-1], 0.6, 0.1))


def test_holt_is_exact_on_linear_series():
    """Property: Holt's linear method reproduces a perfectly linear series
    exactly, for any smoothing parameters."""
    y = 2.0 + 3.0 * np.arange(10)
    for alpha in (0.1, 0.5, 0.9):
        for beta in (0.0, 0.3, 0.5):
            assert np.isclose(holt_forecast(y, alpha, beta), 2.0 + 3.0 * 10)


def test_holt_edge_cases():
    assert np.isnan(holt_forecast(np.array([]), 0.5, 0.1))
    assert holt_forecast(np.array([0.25]), 0.5, 0.1) == 0.25
    path = holt_forecast_path(np.array([[1.0, 2.0, 3.0]]), 0.5, 0.1)
    assert np.isnan(path[0, 0]) and path[0, 1] == 1.0


def test_coupling_ols_recovers_planted_gamma():
    x = np.linspace(-0.05, 0.05, 200)
    r = 0.8 * x
    fit = fit_coupling(r, x)
    assert np.isclose(fit.gamma, 0.8)
    assert fit.significant
    # no variation -> no claim
    flat = fit_coupling(np.zeros(5), np.zeros(5))
    assert flat.gamma == 0.0 and not flat.significant
